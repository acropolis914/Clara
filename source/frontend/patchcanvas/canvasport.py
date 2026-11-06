#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from math import floor

from qt_compat import (
    qCritical,
    QT_VERSION,
    Qt,
    QLineF,
    QPointF,
    QRectF,
    QTimer,
    QCursor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QApplication,
    QGraphicsItem,
    QMenu,
)

def getSystemFont(size=None, weight=None):
    base_font = QApplication.font() if QApplication.instance() else QFont()
    font = QFont(base_font)
    if size is not None and size > 0:
        font.setPixelSize(size)
    if weight is not None:
        font.setWeight(weight)
    return font

def fontHorizontalAdvance(font, string):
    if hasattr(QFontMetrics, "horizontalAdvance"):
        return QFontMetrics(font).horizontalAdvance(string)
    return QFontMetrics(font).width(string)


# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    features,
    options,
    port_mode2str,
    port_type2str,
    CanvasPortType,
    ANTIALIASING_FULL,
    ACTION_PORT_INFO,
    ACTION_PORT_RENAME,
    ACTION_PORTS_CONNECT,
    ACTION_PORTS_DISCONNECT,
    PORT_MODE_INPUT,
    PORT_MODE_OUTPUT,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
)

from .canvaslinemov import CanvasLineMov
from .linealgos import resolve_line_algorithm
from .theme import Theme
from .utils import (
    CanvasGetFullPortName,
    CanvasGetPortConnectionList,
    CanvasGetPortDisplayName,
    log_carla,
)

# ------------------------------------------------------------------------------------------------------------


class CanvasPort(QGraphicsItem):
    def __init__(
        self, group_id, port_id, port_name, port_mode, port_type, is_alternate, parent
    ):
        QGraphicsItem.__init__(self)
        self.setParentItem(parent)

        self.m_group_id = group_id
        self.m_port_id = port_id
        self.m_port_mode = port_mode
        self.m_port_type = port_type
        self.m_port_name = port_name
        self.m_is_alternate = is_alternate
        display_name = self.getDisplayPortName()
        # print(
        #     "PatchCanvas::CanvasPort created: group={!r}, raw={!r}, display={!r}".format(
        #         self.parentItem().getGroupName(), self.m_port_name, display_name
        #     )
        # )
        self.setToolTip(display_name)

        self.m_port_width = 15
        self.m_port_height = canvas.theme.port_height
        self.m_port_font = getSystemFont(
            canvas.theme.port_font_size, canvas.theme.port_font_state
        )

        # Cached theme references - resolved once, not on every paint() call
        self._theme_prefix = None
        self._theme_poly_color = None
        self._theme_poly_color_sel = None
        self._theme_poly_pen = None
        self._theme_poly_pen_sel = None
        self._theme_text_pen = None
        self._theme_text_pen_sel = None
        self._theme_conn_pen = None
        self._rebuildThemeCache()

        self.m_line_mov = None
        self.m_hover_item = None
        self.m_mouse_down = False
        self.m_cursor_moving = False

        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setCacheMode(
            getattr(QGraphicsItem, "DeviceCoordinateCache", getattr(getattr(QGraphicsItem, "CacheMode", None), "DeviceCoordinateCache", None))
        )

        if options.auto_select_items:
            self.setAcceptHoverEvents(True)

    # --- Refactored Helper ---
    def _is_connected_to(self, connection, other_item=None):
        """Replaces the massive repeated if-statements for checking port connections."""
        if not other_item:
            return (
                connection.group_out_id == self.m_group_id
                and connection.port_out_id == self.m_port_id
            ) or (
                connection.group_in_id == self.m_group_id
                and connection.port_in_id == self.m_port_id
            )

        h_group, h_port = other_item.getGroupId(), other_item.getPortId()
        return (
            connection.group_out_id == self.m_group_id
            and connection.port_out_id == self.m_port_id
            and connection.group_in_id == h_group
            and connection.port_in_id == h_port
        ) or (
            connection.group_out_id == h_group
            and connection.port_out_id == h_port
            and connection.group_in_id == self.m_group_id
            and connection.port_in_id == self.m_port_id
        )

    def getGroupId(self):
        return self.m_group_id

    def getPortId(self):
        return self.m_port_id

    def getPortMode(self):
        return self.m_port_mode

    def getPortType(self):
        return self.m_port_type

    def getPortName(self):
        return self.m_port_name

    def getFullPortName(self):
        return self.parentItem().getGroupName() + ":" + self.m_port_name

    def getDisplayPortName(self):

        group_name = self.parentItem().getGroupName()
        display_name = CanvasGetPortDisplayName(group_name, self.m_port_name)
        return display_name
        return group_name + ":" + display_name

    def getPortWidth(self):
        return self.m_port_width

    def getPortHeight(self):
        return self.m_port_height

    def setPortMode(self, port_mode):
        self.m_port_mode = port_mode
        self.update()

    def setPortType(self, port_type):
        self.m_port_type = port_type
        self.update()

    def setPortName(self, port_name):
        metrics = QFontMetrics(self.m_port_font)
        if QT_VERSION >= 0x50B00:
            width1, width2 = (
                metrics.horizontalAdvance(port_name),
                metrics.horizontalAdvance(self.m_port_name),
            )
        else:
            width1, width2 = metrics.width(port_name), metrics.width(self.m_port_name)

        if width1 < width2:
            QTimer.singleShot(0, canvas.scene.update)

        self.m_port_name = port_name
        self.setToolTip(self.getDisplayPortName())
        self.update()

    def setPortWidth(self, port_width):
        if port_width < self.m_port_width:
            QTimer.singleShot(0, canvas.scene.update)
        self.m_port_width = port_width
        self.update()

    def type(self):
        return CanvasPortType

    def hoverEnterEvent(self, event):
        self.setToolTip(self.getDisplayPortName())
        if options.auto_select_items:
            self.setSelected(True)
        QGraphicsItem.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        if options.auto_select_items:
            self.setSelected(False)
        QGraphicsItem.hoverLeaveEvent(self, event)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MiddleButton
            or event.source() == Qt.MouseEventSynthesizedByApplication
        ):
            event.ignore()
            return

        if event.modifiers() & Qt.ControlModifier:
            parent = self.parentItem()
            if parent:
                event.accept()
                parent.setSelected(not parent.isSelected())
                return

        if self.m_mouse_down:
            self.handleMouseRelease()
        self.m_hover_item = None
        self.m_mouse_down = bool(event.button() == Qt.LeftButton)
        self.m_cursor_moving = False
        QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if not self.m_mouse_down:
            QGraphicsItem.mouseMoveEvent(self, event)
            return

        event.accept()

        if not self.m_cursor_moving:
            self.setCursor(QCursor(Qt.CrossCursor))
            self.m_cursor_moving = True
            for connection in canvas.connection_list:
                if self._is_connected_to(connection):
                    connection.widget.setLocked(True)

        if not self.m_line_mov:
            self.m_line_mov = CanvasLineMov(
                self.m_port_mode, self.m_port_type, self,
                shape=resolve_line_algorithm().name,
            )
            canvas.last_z_value += 1
            self.m_line_mov.setZValue(canvas.last_z_value)
            canvas.last_z_value += 1
            self.parentItem().setZValue(canvas.last_z_value)

        item = None
        sp = event.scenePos()
        # Fast query with an 8px leeway box around cursor using fast bounding rect intersection
        leeway_rect = QRectF(sp.x() - 8.0, sp.y() - 8.0, 16.0, 16.0)
        mode = getattr(Qt, "IntersectsItemBoundingRect", getattr(getattr(Qt, "ItemSelectionMode", None), "IntersectsItemBoundingRect", Qt.IntersectsItemShape))
        items = canvas.scene.items(leeway_rect, mode, Qt.AscendingOrder)
        for _, itemx in enumerate(items):
            if itemx.type() != CanvasPortType or itemx == self:
                continue
            if item is None or itemx.parentItem().zValue() > item.parentItem().zValue():
                item = itemx

        if self.m_hover_item and self.m_hover_item != item:
            self.m_hover_item.setSelected(False)

        if item is not None:
            if (
                item.getPortMode() != self.m_port_mode
                and item.getPortType() == self.m_port_type
            ):
                item.setSelected(True)
                self.m_hover_item = item
            else:
                self.m_hover_item = None
        else:
            self.m_hover_item = None

        self.m_line_mov.updateLinePos(event.scenePos())

    def handleMouseRelease(self):
        if self.m_mouse_down:
            if self.m_line_mov is not None:
                item = self.m_line_mov
                self.m_line_mov = None
                canvas.scene.removeItem(item)
                del item

            for connection in canvas.connection_list:
                if self._is_connected_to(connection):
                    connection.widget.setLocked(False)

            if self.m_hover_item:
                for connection in canvas.connection_list:
                    if self._is_connected_to(connection, self.m_hover_item):
                        log_carla(f"CanvasPort.handleMouseRelease: disconnecting connId={connection.connection_id}")
                        canvas.callback(
                            ACTION_PORTS_DISCONNECT, connection.connection_id, 0, ""
                        )
                        break
                else:
                    def _effective_id(w):
                        pd = getattr(w, "_port_dict", None)
                        return getattr(pd, "port_id", getattr(w, "m_port_id", -1))

                    eff_self = _effective_id(self)
                    eff_hover = _effective_id(self.m_hover_item)
                    if self.m_port_mode == PORT_MODE_OUTPUT:
                        conn = "%i:%i:%i:%i" % (
                            self.m_group_id,
                            eff_self,
                            self.m_hover_item.getGroupId(),
                            eff_hover,
                        )
                    else:
                        conn = "%i:%i:%i:%i" % (
                            self.m_hover_item.getGroupId(),
                            eff_hover,
                            self.m_group_id,
                            eff_self,
                        )
                    log_carla("request " + conn.replace(":", " → ", 2), level="debug")
                    if eff_self < 0 or eff_hover < 0:
                        # Placeholder port that never bound to the engine; refuse instead of
                        # sending an id the engine cannot resolve.
                        hover = self.m_hover_item.getPortName() if hasattr(self.m_hover_item, "getPortName") else "?"
                        try:
                            from .patchcanvas import canvas as _pc_canvas
                            neg = [p.port_id for p in _pc_canvas.port_list if getattr(p, "port_id", 0) < 0]
                            parent = self.parentItem()
                            pname = getattr(parent, "m_group_name", None)
                            shell = getattr(parent, "_shell", None)
                        except Exception:
                            neg, pname, shell = [], None, None
                        log_carla(
                            f"CanvasPort.handleMouseRelease: refusing unbound port {conn} "
                            f"(self='{self.m_port_name}' hover='{hover}' parent='{pname}' "
                            f"shell={shell} negative_ports={neg[:10]})",
                            level="warn",
                        )
                        # remove the clicked ghost after this event returns (never delete self mid-handler)
                        try:
                            from .patchcanvas import removePortWidget
                            QTimer.singleShot(0, lambda w=self: removePortWidget(w))
                        except Exception:
                            pass
                    else:
                        canvas.callback(ACTION_PORTS_CONNECT, 0, 0, conn)

                canvas.scene.clearSelection()

        if self.m_cursor_moving:
            self.unsetCursor()

        self.m_hover_item = None
        self.m_mouse_down = False
        self.m_cursor_moving = False

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.handleMouseRelease()
        QGraphicsItem.mouseReleaseEvent(self, event)

    def contextMenuEvent(self, event):
        event.accept()
        canvas.scene.clearSelection()
        self.setSelected(True)

        menu = QMenu()
        discMenu = QMenu("Disconnect", menu)
        conn_list = CanvasGetPortConnectionList(self.m_group_id, self.m_port_id)

        if len(conn_list) > 0:
            for conn_id, group_id, port_id in conn_list:
                act_x_disc = discMenu.addAction(
                    CanvasGetFullPortName(group_id, port_id)
                )
                act_x_disc.setData(conn_id)
                act_x_disc.triggered.connect(canvas.qobject.PortContextMenuDisconnect)
        else:
            act_x_disc = discMenu.addAction("No connections")
            act_x_disc.setEnabled(False)

        menu.addMenu(discMenu)
        act_x_disc_all = menu.addAction("Disconnect &All")
        act_x_sep_1 = menu.addSeparator()
        act_x_info = menu.addAction("Get &Info")
        act_x_rename = menu.addAction("&Rename")

        act_x_info.setVisible(features.port_info)
        act_x_rename.setVisible(features.port_rename)
        act_x_sep_1.setVisible(features.port_info and features.port_rename)

        act_selected = menu.exec_(event.screenPos())

        if act_selected == act_x_disc_all:
            self.triggerDisconnect(conn_list)
        elif act_selected == act_x_info:
            canvas.callback(ACTION_PORT_INFO, self.m_group_id, self.m_port_id, "")
        elif act_selected == act_x_rename:
            canvas.callback(ACTION_PORT_RENAME, self.m_group_id, self.m_port_id, "")

    def setPortSelected(self, yesno):
        for connection in canvas.connection_list:
            if self._is_connected_to(connection):
                connection.widget.updateLineSelected()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.setPortSelected(value)
        return QGraphicsItem.itemChange(self, change, value)

    def triggerDisconnect(self, conn_list=None):
        if not conn_list:
            conn_list = CanvasGetPortConnectionList(self.m_group_id, self.m_port_id)
        for conn_id, _, _ in conn_list:
            canvas.callback(ACTION_PORTS_DISCONNECT, conn_id, 0, "")

    def _rebuildThemeCache(self):
        """Resolve theme attributes once - called at creation and on theme change."""
        _prefix_map = {
            PORT_TYPE_AUDIO_JACK: "port_audio_jack",
            PORT_TYPE_MIDI_JACK:  "port_midi_jack",
            PORT_TYPE_MIDI_ALSA:  "port_midi_alsa",
            PORT_TYPE_PARAMETER:  "port_parameter",
        }
        prefix = _prefix_map.get(self.m_port_type)
        if not prefix:
            return
        theme = canvas.theme
        self._theme_prefix        = prefix
        self._theme_poly_color     = getattr(theme, f"{prefix}_bg")
        self._theme_poly_color_sel = getattr(theme, f"{prefix}_bg_sel")
        self._theme_poly_pen       = getattr(theme, f"{prefix}_pen")
        self._theme_poly_pen_sel   = getattr(theme, f"{prefix}_pen_sel")
        self._theme_text_pen       = getattr(theme, f"{prefix}_text")
        self._theme_text_pen_sel   = getattr(theme, f"{prefix}_text_sel")
        self._theme_conn_pen       = QPen(getattr(theme, f"{prefix}_pen_sel"))

    def updateTheme(self):
        self.m_port_height = canvas.theme.port_height
        self.m_port_font = getSystemFont(
            canvas.theme.port_font_size, canvas.theme.port_font_state
        )
        self._rebuildThemeCache()
        self.update()

    def boundingRect(self):
        return QRectF(0, 0, self.m_port_width + 12, self.m_port_height)

    def paint(self, painter, option, widget):
        painter.save()
        painter.setRenderHint(
            QPainter.Antialiasing, bool(options.antialiasing == ANTIALIASING_FULL or canvas.theme.port_mode == Theme.THEME_PORT_SOCKET)
        )

        # Use pre-resolved theme attrs - no dict/getattr on every frame
        if self._theme_prefix is None:
            qCritical(
                f"PatchCanvas::CanvasPort.paint() - invalid port type '{port_type2str(self.m_port_type)}'"
            )
            painter.restore()
            return

        selected = self.isSelected()
        poly_color = self._theme_poly_color_sel if selected else self._theme_poly_color
        poly_pen   = self._theme_poly_pen_sel   if selected else self._theme_poly_pen
        text_pen   = self._theme_text_pen_sel   if selected else self._theme_text_pen
        conn_pen   = self._theme_conn_pen

        poly_pen = QPen(poly_pen)
        poly_pen.setWidthF(poly_pen.widthF() + 0.00001)

        if self.m_is_alternate:
            poly_color = poly_color.darker(180)

        lineHinting = poly_pen.widthF() / 2
        height = float(canvas.theme.port_height)
        radius = (height - (2 * lineHinting)) / 2.0
        font_metrics = QFontMetrics(self.m_port_font)
        text_y = (
            height - font_metrics.ascent() - font_metrics.descent()
        ) / 2 + font_metrics.ascent()

        # --- Blender-style Socket Drawing (dots on edges, label text on body) ---
        if canvas.theme.port_mode == Theme.THEME_PORT_SOCKET:
            socket_r = 4.0
            cy = height / 2.0
            if self.m_port_mode == PORT_MODE_INPUT:
                cx = 5.0
                socket_rect = QRectF(cx - socket_r, cy - socket_r, socket_r * 2.0, socket_r * 2.0)
                text_pos = QPointF(cx + socket_r + 5.0, text_y)
            elif self.m_port_mode == PORT_MODE_OUTPUT:
                right_x = self.m_port_width + 12.0
                cx = right_x - 5.0
                socket_rect = QRectF(cx - socket_r, cy - socket_r, socket_r * 2.0, socket_r * 2.0)
                text_w = fontHorizontalAdvance(self.m_port_font, self.m_port_name)
                text_x = max(1.0, (cx - socket_r - 4.0) - text_w)
                text_pos = QPointF(text_x, text_y)
            else:
                painter.restore()
                return

            painter.setBrush(poly_color)
            painter.setPen(poly_pen)
            painter.drawEllipse(socket_rect)

            if selected:
                ring_pen = QPen(poly_pen)
                ring_pen.setWidthF(1.0)
                painter.setPen(ring_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(cx - socket_r - 2.0, cy - socket_r - 2.0, (socket_r + 2.0) * 2.0, (socket_r + 2.0) * 2.0))

            painter.setPen(text_pen)
            painter.setFont(self.m_port_font)
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.drawText(QPointF(round(text_pos.x()), round(text_pos.y())), self.m_port_name)
            painter.restore()
            return

        path = QPainterPath()

        # --- Refactored Semicircle Path Drawing ---
        if self.m_port_mode == PORT_MODE_INPUT:
            text_pos = QPointF(3, text_y)
            base_x = self.m_port_width + 5 - lineHinting

            path.moveTo(lineHinting, lineHinting)
            path.lineTo(base_x, lineHinting)

            if canvas.theme.port_mode == Theme.THEME_PORT_POLYGON:
                arc_rect = QRectF(
                    base_x - radius, lineHinting, radius * 2, height - (2 * lineHinting)
                )
                path.arcTo(arc_rect, 90, -180)
            elif canvas.theme.port_mode == Theme.THEME_PORT_SQUARE:
                path.lineTo(base_x, height - lineHinting)
            else:
                qCritical(
                    f"PatchCanvas::CanvasPort.paint() - invalid theme mode '{canvas.theme.port_mode}'"
                )
                painter.restore()
                return

            path.lineTo(lineHinting, height - lineHinting)
            path.closeSubpath()

        elif self.m_port_mode == PORT_MODE_OUTPUT:
            text_pos = QPointF(9, text_y)
            base_x = 7 + lineHinting
            right_x = self.m_port_width + 12 - lineHinting

            path.moveTo(right_x, lineHinting)
            path.lineTo(base_x, lineHinting)

            if canvas.theme.port_mode == Theme.THEME_PORT_POLYGON:
                arc_rect = QRectF(
                    base_x - radius, lineHinting, radius * 2, height - (2 * lineHinting)
                )
                path.arcTo(arc_rect, 90, 180)
            elif canvas.theme.port_mode == Theme.THEME_PORT_SQUARE:
                path.lineTo(base_x, height - lineHinting)
            else:
                qCritical(
                    f"PatchCanvas::CanvasPort.paint() - invalid theme mode '{canvas.theme.port_mode}'"
                )
                painter.restore()
                return

            path.lineTo(right_x, height - lineHinting)
            path.closeSubpath()

        else:
            qCritical(
                f"PatchCanvas::CanvasPort.paint() - invalid port mode '{port_mode2str(self.m_port_mode)}'"
            )
            painter.restore()
            return

        portRect = path.boundingRect().adjusted(
            -lineHinting + 1, -lineHinting + 1, lineHinting - 1, lineHinting - 1
        )

        if canvas.theme.port_bg_pixmap:
            painter.drawTiledPixmap(
                portRect, canvas.theme.port_bg_pixmap, portRect.topLeft()
            )
        else:
            painter.setBrush(poly_color)

        painter.setPen(poly_pen)
        painter.drawPath(path)

        painter.setPen(text_pen)
        painter.setFont(self.m_port_font)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.drawText(QPointF(round(text_pos.x()), round(text_pos.y())), self.m_port_name)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if canvas.theme.idx == Theme.THEME_OOSTUDIO and canvas.theme.port_bg_pixmap:
            conn_pen.setCosmetic(True)
            conn_pen.setWidthF(0.4)
            painter.setPen(conn_pen)

            connLineX = (
                portRect.left() + 1
                if self.m_port_mode == PORT_MODE_INPUT
                else portRect.right() - 1
            )

            conn_path = QPainterPath()
            conn_path.addRect(
                QRectF(connLineX - 1, portRect.top(), 2, portRect.height())
            )
            painter.fillPath(conn_path, conn_pen.brush())
            painter.drawLine(
                QLineF(connLineX, portRect.top(), connLineX, portRect.bottom())
            )

        painter.restore()


# ------------------------------------------------------------------------------------------------------------
