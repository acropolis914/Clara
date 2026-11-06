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
from canvas_context_toolbar import CanvasContextToolBarOverlay
from canvas_logic import findStereoPartnerConnection
from canvas_toolbar import CanvasToolBarOverlay
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
