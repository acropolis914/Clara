#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    Qt,
    QPointF,
    QColor,
    QLinearGradient,
    QRadialGradient,
    QPainter,
    QPen,
    QTimer,
    QGraphicsPathItem,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    options,
    ACTION_PORTS_DISCONNECT,
    CanvasBoxType,
    EYECANDY_FULL,
    PORT_MODE_OUTPUT,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
)

from .linealgos import (
    get_line_algorithm,
    LineContext,
    DIRECTION_OUTPUT,
)

from .canvasportglow import CanvasPortGlow

# ------------------------------------------------------------------------------------------------------------

_selection_refresh_scheduled = False


def scheduleSelectionStyleRefresh():
    """Coalesce one global refresh after a batch of selection changes (select all)."""
    global _selection_refresh_scheduled
    if _selection_refresh_scheduled:
        return
    _selection_refresh_scheduled = True

    def _run():
        global _selection_refresh_scheduled
        _selection_refresh_scheduled = False
        for connection in getattr(canvas, "connection_list", ()):
            widget = getattr(connection, "widget", None)
            if widget is not None and hasattr(widget, "refreshSelectionStyle"):
                widget.refreshSelectionStyle()

    QTimer.singleShot(0, _run)


def _allNodesSelected():
    """True when every node box is selected, used to skip the selected-cable style."""
    try:
        scene = canvas.scene
        if scene is None:
            return False
        # Only count what is actually visible: filtered/hidden clients still exist
        # in group_list but cannot be selected, which would keep this false forever.
        boxes = [item for item in scene.items()
                 if item.type() == CanvasBoxType and item.isVisible()]
        if not boxes:
            return False
        return all(item.isSelected() for item in boxes)
    except Exception:
        return False


class CanvasLine(QGraphicsPathItem):
    """
    Unified connection line item rendering both Bézier curves, straight lines,
    and stepped/orthogonal paths, with configurable stroke patterns (solid, dotted, dashed).
    """
    def __init__(self, item1, item2, parent, shape=None, stroke=None, opacity=None):
        QGraphicsPathItem.__init__(self)
        self.setParentItem(parent)

        self.item1 = item1
        self.item2 = item2
        self.m_shape = shape if shape is not None else getattr(options, "line_style", "bezier")
        self.m_stroke = stroke if stroke is not None else getattr(options, "line_stroke", "solid")
        self.m_opacity = opacity if opacity is not None else getattr(options, "line_opacity", 100)
        self.m_algorithm = get_line_algorithm(self.m_shape)
        self.m_base_algorithm = self.m_algorithm

        # Per-selection style override (routing, stroke, thickness)
        self.m_active_stroke = self.m_stroke
        self.m_sel_shape = None
        self.m_sel_algorithm = None
        self.m_width_override = None
        self._selection_style_dirty = True

        self.m_locked = False
        self.m_lineSelected = None  # None sentinel - ensures updateLineGradient() fires on first call

        self._cached_pen = None
        self._cached_cosm_pen = None
        self._ctx = None

        self.setBrush(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(None)
        self.updateLinePos()

    def setShape(self, shape):
        if self.m_shape != shape:
            self.m_shape = shape
            self.m_base_algorithm = get_line_algorithm(shape)
            self._applySelectionStyle()
            self._cached_pen = None
            self.prepareGeometryChange()
            self.updateLinePos()
            self.update()

    def getShape(self):
        return self.m_shape

    def setStroke(self, stroke):
        if self.m_stroke != stroke:
            self.m_stroke = stroke
            self._applySelectionStyle()
            self._cached_pen = None
            self.prepareGeometryChange()
            self.updateLineGradient()
            self.update()

    def getStroke(self):
        return self.m_stroke

    def setOpacityVal(self, opacity):
        if self.m_opacity != opacity:
            self.m_opacity = opacity
            self._cached_pen = None
            self.prepareGeometryChange()
            self.updateLineGradient()
            self.update()

    def getOpacityVal(self):
        return self.m_opacity

    def isLocked(self):
        return self.m_locked

    def setLocked(self, yesno):
        self.m_locked = yesno

    def isLineSelected(self):
        return self.m_lineSelected

    def updateLineSelected(self):
        if self.m_locked:
            return

        p1 = self.item1.parentItem()
        p2 = self.item2.parentItem()
        yesno = (self.item1.isSelected() or self.item2.isSelected() or
                 (p1 is not None and p1.isSelected()) or 
                 (p2 is not None and p2.isSelected()))

        if yesno == self.m_lineSelected and not self._selection_style_dirty:
            return  # No state change - skip expensive gradient + QPen recompute

        self.m_lineSelected = yesno
        style_changed = self._applySelectionStyle()
        self._selection_style_dirty = False
        self.updateLineGradient()

        # Selection-aware algorithms need a re-route; the selected-cable style may
        # also switch the algorithm (linear/bezier/...), so rebuild in both cases.
        if style_changed or (self.m_algorithm.selection_sensitive and self._ctx is not None):
            QTimer.singleShot(0, self.updateLinePos)

    def refreshSelectionStyle(self):
        """Re-apply the selected-cable options without waiting for a selection change."""
        self._selection_style_dirty = True
        self.updateLineSelected()

    def _selectionOverrideActive(self):
        if not self.m_lineSelected:
            return False
        if not getattr(options, "selected_line_enabled", False):
            return False
        if getattr(options, "selected_line_skip_all", True) and _allNodesSelected():
            return False
        return True

    def _applySelectionStyle(self):
        """Switch routing/stroke/thickness for a selected cable; returns True on change."""
        active = self._selectionOverrideActive()
        shape = getattr(options, "selected_line_style", "") if active else ""
        stroke = getattr(options, "selected_line_stroke", "inherit") if active else "inherit"
        thickness = getattr(options, "selected_line_thickness", 5) if active else None

        algorithm = self.m_base_algorithm
        if shape:
            if shape != self.m_sel_shape or self.m_sel_algorithm is None:
                self.m_sel_shape = shape
                self.m_sel_algorithm = get_line_algorithm(shape)
            algorithm = self.m_sel_algorithm
        else:
            # Drop both, or a later reselect would reuse the stale shape with a
            # cleared algorithm and paint with None.
            self.m_sel_shape = None
            self.m_sel_algorithm = None

        active_stroke = self.m_stroke if stroke in (None, "", "inherit") else stroke

        changed = (algorithm is not self.m_algorithm
                   or active_stroke != self.m_active_stroke
                   or thickness != self.m_width_override)
        self.m_algorithm = algorithm
        self.m_active_stroke = active_stroke
        self.m_width_override = thickness
        if changed:
            self._cached_pen = None
        return changed

    def triggerDisconnect(self):
        for connection in canvas.connection_list:
            if (connection.port_out_id == self.item1.getPortId() and connection.port_in_id == self.item2.getPortId()):
                canvas.callback(ACTION_PORTS_DISCONNECT, connection.connection_id, 0, "")
                break

    def _sceneEndpoints(self):
        if self.item1.getPortMode() != PORT_MODE_OUTPUT:
            return None

        # Check if item1's box is in a collapsed container
        box1 = self.item1.parentItem()
        c1 = getattr(box1, "_canvas_container", None) if box1 else None
        if c1 and getattr(c1, "m_collapsed", False):
            start = c1.getHeaderPortScenePos(self.item1, is_output=True)
        else:
            rect1 = self.item1.sceneBoundingRect()
            start = QPointF(rect1.right(), rect1.top() + float(canvas.theme.port_height) / 2)

        # Check if item2's box is in a collapsed container
        box2 = self.item2.parentItem()
        c2 = getattr(box2, "_canvas_container", None) if box2 else None
        if c2 and getattr(c2, "m_collapsed", False):
            end = c2.getHeaderPortScenePos(self.item2, is_output=False)
        else:
            rect2 = self.item2.sceneBoundingRect()
            end = QPointF(rect2.left(), rect2.top() + float(canvas.theme.port_height) / 2)

        return start, end

    def getEndpoints(self):
        pair = self._sceneEndpoints()
        if pair is None:
            return None
        return (pair[0], pair[1], DIRECTION_OUTPUT)

    def updateTheme(self):
        """Re-read theme colours after a theme switch."""
        self._pulse_c1 = None
        self._pulse_c2 = None
        self.updateLineGradient()
        self.updateLineSelected()
        self.updateLinePos()

    def updateLinePos(self):
        pair = self._sceneEndpoints()
        if pair is None:
            return

        start, end = pair
        self._ctx = LineContext(
            start, end, DIRECTION_OUTPUT,
            port1=self.item1, port2=self.item2, connection=self, canvas=canvas,
        )
        self.prepareGeometryChange()
        self.setPath(self.m_algorithm.build_path(self._ctx))
        self.updateLineGradient()
        self.updateLineSelected()

    def type(self):
        return self.m_algorithm.line_type

    def updateLineGradient(self):
        pair = self._sceneEndpoints()
        if pair is None:
            return
        p1_scene, p2_scene = pair

        # Map scene endpoints to local item coordinates for QPainter
        p1 = self.mapFromScene(p1_scene)
        p2 = self.mapFromScene(p2_scene)
        port_gradient = QLinearGradient(p1, p2)

        # Scale alpha with user line opacity setting (20% - 100%)
        opacity_factor = max(0.2, min(1.0, float(self.m_opacity) / 100.0))

        bg_color = canvas.theme.canvas_bg
        bg_lum = 0.2126 * (bg_color.redF() ** 2.2) + 0.7152 * (bg_color.greenF() ** 2.2) + 0.0722 * (bg_color.blueF() ** 2.2)

        def ensure_contrast(c):
            col = QColor(c)
            # Calculate perceived relative luminance
            c_lum = 0.2126 * (col.redF() ** 2.2) + 0.7152 * (col.greenF() ** 2.2) + 0.0722 * (col.blueF() ** 2.2)
            contrast = (max(c_lum, bg_lum) + 0.05) / (min(c_lum, bg_lum) + 0.05)
            # If contrast against background is too low (< 2.2:1), adjust lightness
            if contrast < 2.2:
                h = col.hslHueF()
                s = col.hslSaturationF()
                l = col.lightnessF()
                if bg_lum < 0.5:
                    # Dark background: boost lightness up until contrast is adequate
                    while l < 0.90:
                        l = min(0.92, l + 0.10)
                        test_c = QColor.fromHslF(max(0.0, h), max(0.2, s), l)
                        test_lum = 0.2126 * (test_c.redF() ** 2.2) + 0.7152 * (test_c.greenF() ** 2.2) + 0.0722 * (test_c.blueF() ** 2.2)
                        if (test_lum + 0.05) / (bg_lum + 0.05) >= 2.5:
                            return test_c
                    return QColor.fromHslF(max(0.0, h), max(0.2, s), l)
                else:
                    # Light background: reduce lightness down until contrast is adequate
                    while l > 0.15:
                        l = max(0.10, l - 0.10)
                        test_c = QColor.fromHslF(max(0.0, h), max(0.2, s), l)
                        test_lum = 0.2126 * (test_c.redF() ** 2.2) + 0.7152 * (test_c.greenF() ** 2.2) + 0.0722 * (test_c.blueF() ** 2.2)
                        if (bg_lum + 0.05) / (test_lum + 0.05) >= 2.5:
                            return test_c
                    return QColor.fromHslF(max(0.0, h), max(0.2, s), l)
            return col

        def get_color(color_val):
            c = ensure_contrast(color_val)
            # Default unselected line has clear visibility (190 base alpha instead of muddy 127)
            base_alpha = 255 if self.m_lineSelected else 190
            c.setAlpha(int(base_alpha * opacity_factor))
            return c

        def get_port_color(port):
            parent = port.parentItem()
            if parent is not None and hasattr(parent, "getCustomColor"):
                custom_c = parent.getCustomColor()
                if custom_c is not None:
                    return custom_c

            ptype = port.getPortType()
            theme = canvas.theme
            if ptype == PORT_TYPE_AUDIO_JACK:
                return theme.line_audio_jack_sel if self.m_lineSelected else theme.line_audio_jack
            elif ptype == PORT_TYPE_MIDI_JACK:
                return theme.line_midi_jack_sel if self.m_lineSelected else theme.line_midi_jack
            elif ptype == PORT_TYPE_MIDI_ALSA:
                return theme.line_midi_alsa_sel if self.m_lineSelected else theme.line_midi_alsa
            elif ptype == PORT_TYPE_PARAMETER:
                return theme.line_parameter_sel if self.m_lineSelected else theme.line_parameter
            return theme.line_audio_jack

        port_gradient.setColorAt(0.0, get_color(get_port_color(self.item1)))
        port_gradient.setColorAt(1.0, get_color(get_port_color(self.item2)))

        pen_style = Qt.SolidLine
        if self.m_active_stroke == "dotted":
            pen_style = Qt.DotLine
        elif self.m_active_stroke == "dashed":
            pen_style = Qt.DashLine

        cap_style = self.m_algorithm.cap_style

        # Cache built pen so paint() never allocates per frame
        self._cached_pen = QPen(port_gradient, 2.00001, pen_style, cap_style)
        self.setPen(self._cached_pen)

        # Pre-build cosmetic overlay pen - stored for reuse
        cosm = QPen(self._cached_pen)
        cosm.setCosmetic(True)
        cosm.setWidthF(1.00001)
        self._cached_cosm_pen = cosm

    def paint(self, painter, option, widget):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, bool(options.antialiasing))

        # Let the algorithm draw itself (arrowheads, bundles, animated flow, ...) if it wants to
        if self._ctx is not None and self.m_algorithm.paint(painter, self._ctx, self.path()):
            # Still overlay the signal-flow pulse on top of custom-drawn cables
            painter.setOpacity(1.0)
            self._draw_signal_pulse(painter, self.path())
            painter.restore()
            return

        pen = self._cached_pen if self._cached_pen is not None else self.pen()
        scale = canvas.scene.getScaleFactor() if hasattr(canvas.scene, "getScaleFactor") else 1.0
        # Dynamic cable thickness: maintain clear visibility across zoom levels while remaining crisp when zoomed in
        if self.m_width_override:
            effective_width = max(2.0, min(14.0, float(self.m_width_override) / (scale ** 0.6)))
        else:
            effective_width = max(1.5, min(6.0, 2.2 / (scale ** 0.6)))
        if abs(pen.widthF() - effective_width) > 0.05:
            pen = QPen(pen)
            pen.setWidthF(effective_width)

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

        # Cosmetic glow overlay - skip entirely when eye candy is off
        if options.eyecandy and not options.software_render:
            cosm_pen = getattr(self, "_cached_cosm_pen", None)
            if cosm_pen is not None:
                painter.setPen(cosm_pen)
                painter.setBrush(Qt.NoBrush)
                painter.setOpacity(0.2)
                painter.drawPath(self.path())

        # Signal / event flow pulse travelling along the cable
        painter.setOpacity(1.0)
        self._draw_signal_pulse(painter, self.path())

        painter.restore()

    def _endpointGroupIds(self):
        out_id = in_id = None
        try:
            if self.item1 is not None:
                box = self.item1.parentItem()
                out_id = box.getGroupId() if box is not None else None
        except Exception:
            out_id = None
        try:
            if self.item2 is not None:
                box = self.item2.parentItem()
                in_id = box.getGroupId() if box is not None else None
        except Exception:
            in_id = None
        return out_id, in_id

    def _signalLevel(self):
        from . import signalflow
        out_id, _in_id = self._endpointGroupIds()
        # A cable carries signal from its source only: a loud destination must not
        # make an idle cable pulse.
        return signalflow.state.flow.get(out_id, 0.0)

    def _draw_signal_pulse(self, painter, path):
        from . import signalflow
        if not signalflow.state.enabled:
            return

        level = self._signalLevel()
        if level <= 0.03:
            return

        offset = getattr(self, "_signal_offset", None)
        if offset is None:
            offset = (id(self) % 997) / 997.0  # stable, de-synchronised per cable
            self._signal_offset = offset

        t = (signalflow.state.phase + offset) % 1.0

        head_radius = 3.5 + 9.0 * level
        alpha = int(min(255.0, 150.0 + 105.0 * level))

        # Interpolate pulse color along connection chain: blend source node color to destination node color
        c1 = getattr(self, "_pulse_c1", None)
        c2 = getattr(self, "_pulse_c2", None)
        if c1 is None or c2 is None:
            c1 = QColor(canvas.theme.color_accent)
            c2 = QColor(canvas.theme.color_accent)
            try:
                for port, attr in ((self.item1, "_pulse_c1"), (self.item2, "_pulse_c2")):
                    col = None
                    parent = port.parentItem() if port is not None else None
                    if parent is not None and hasattr(parent, "getCustomColor"):
                        custom_c = parent.getCustomColor()
                        if custom_c is not None:
                            col = QColor(custom_c)
                    if col is None and port is not None:
                        ptype = port.getPortType()
                        theme = canvas.theme
                        if ptype == PORT_TYPE_AUDIO_JACK:
                            col = theme.line_audio_jack
                        elif ptype in (PORT_TYPE_MIDI_JACK, PORT_TYPE_MIDI_ALSA):
                            col = theme.line_midi_jack
                        elif ptype == PORT_TYPE_PARAMETER:
                            col = theme.line_parameter
                    if col is not None:
                        setattr(self, attr, col)
                c1 = getattr(self, "_pulse_c1", c1)
                c2 = getattr(self, "_pulse_c2", c2)
            except Exception:
                pass

        def _interp_color(pos):
            # Blend c1 -> c2 along path parameter pos
            r = int(c1.red() + (c2.red() - c1.red()) * pos)
            g = int(c1.green() + (c2.green() - c1.green()) * pos)
            b = int(c1.blue() + (c2.blue() - c1.blue()) * pos)
            return r, g, b

        # Short comet tail trailing behind the head for a clearer sense of flow
        tail_len = 0.05 + 0.10 * level
        for i in range(1, 5):
            tt = (t - tail_len * i / 4.0) % 1.0
            try:
                tp = path.pointAtPercent(tt)
            except Exception:
                break
            if tp is None:
                break
            frac = 1.0 - i / 5.0
            r = head_radius * frac
            a = int(alpha * frac * 0.6)
            tr, tg, tb = _interp_color(tt)
            tail_grad = QRadialGradient(tp, r)
            core = QColor(canvas.theme.color_text)
            core.setAlpha(a)
            tail_grad.setColorAt(0.0, core)
            tail_grad.setColorAt(0.5, QColor(tr, tg, tb, int(a * 0.6)))
            tail_grad.setColorAt(1.0, QColor(tr, tg, tb, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(tail_grad)
            painter.drawEllipse(tp, r, r)

        try:
            point = path.pointAtPercent(t)
        except Exception:
            return
        if point is None:
            return

        pr, pg, pb = _interp_color(t)
        gradient = QRadialGradient(point, head_radius)
        core = QColor(canvas.theme.color_text)
        core.setAlpha(alpha)
        gradient.setColorAt(0.0, core)
        gradient.setColorAt(0.35, QColor(min(255, pr + 60), min(255, pg + 60), min(255, pb + 60), int(alpha * 0.85)))
        gradient.setColorAt(0.7, QColor(pr, pg, pb, int(alpha * 0.5)))
        gradient.setColorAt(1.0, QColor(pr, pg, pb, 0))

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(point, head_radius, head_radius)

# ------------------------------------------------------------------------------------------------------------
# Backward Compatibility Alias

class CanvasBezierLine(CanvasLine):
    def __init__(self, item1, item2, parent, stroke="solid"):
        CanvasLine.__init__(self, item1, item2, parent, shape="bezier", stroke=stroke)
