#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    pyqtSlot,
    qCritical,
    qFatal,
    qWarning,
    QObject,
    QPointF,
    QRectF,
    QTimer,
    QGraphicsObject,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    features,
    options,
    group_dict_t,
    port_dict_t,
    connection_dict_t,
    bool2str,
    icon2str,
    split2str,
    port_mode2str,
    port_type2str,
    CanvasIconType,
    CanvasRubberbandType,
    CanvasContainerType,
    ACTION_PORTS_DISCONNECT,
    EYECANDY_FULL,
    ICON_APPLICATION,
    ICON_HARDWARE,
    ICON_LADISH_ROOM,
    PORT_MODE_INPUT,
    PORT_MODE_OUTPUT,
    PORT_TYPE_AUDIO_JACK,
    SPLIT_YES,
    SPLIT_NO,
    SPLIT_UNDEF,
    MAX_PLUGIN_ID_ALLOWED,
)

from .canvasbox import CanvasBox
from .canvasbezierline import CanvasBezierLine
from .canvasline import CanvasLine
from .linealgos import resolve_line_algorithm
from .arrangealgos import layout_algorithms, resolve_layout_algorithm
from .theme import Theme, getDefaultTheme, getThemeName
from .utils import (
    CanvasCallback,
    CanvasGetNewGroupPos,
    CanvasGetPortDisplayName,
    CanvasItemFX,
    CanvasRemoveItemFX,
    log_carla,
)

# FIXME
from . import *
from .scene import PatchScene

from utils import QSafeSettings

# ------------------------------------------------------------------------------------------------------------


class CanvasObject(QObject):
    def __init__(self, parent=None):
        QObject.__init__(self, parent)

    @pyqtSlot()
    def AnimationFinishedShow(self):
        animation = self.sender()
        if animation:
            animation.forceStop()
            canvas.animation_list.remove(animation)

    @pyqtSlot()
    def AnimationFinishedHide(self):
        animation = self.sender()
        if animation:
            animation.forceStop()
            canvas.animation_list.remove(animation)
            item = animation.item()
            if item:
                if isinstance(item, QGraphicsObject):
                    item.blockSignals(True)
                    item.hide()
                    item.blockSignals(False)
                else:
                    item.hide()

    @pyqtSlot()
    def AnimationFinishedDestroy(self):
        animation = self.sender()
        if animation:
            animation.forceStop()
            canvas.animation_list.remove(animation)
            item = animation.item()
            if item:
                CanvasRemoveItemFX(item)

    @pyqtSlot()
    def PortContextMenuConnect(self):
        try:
            sources, targets = self.sender().data()
        except Exception:
            return

        for port_type in (
            PORT_TYPE_AUDIO_JACK,
            PORT_TYPE_MIDI_JACK,
            PORT_TYPE_MIDI_ALSA,
            PORT_TYPE_PARAMETER,
        ):
            source_ports = sources[port_type]
            target_ports = targets[port_type]

            source_ports_len = len(source_ports)
            target_ports_len = len(target_ports)

            if source_ports_len == 0 or target_ports_len == 0:
                continue

            for i in range(min(source_ports_len, target_ports_len)):
                data = "%i:%i:%i:%i" % (
                    source_ports[i][0],
                    source_ports[i][1],
                    target_ports[i][0],
                    target_ports[i][1],
                )
                CanvasCallback(ACTION_PORTS_CONNECT, 0, 0, data)

            if source_ports_len == 1 and target_ports_len > 1:
                for i in range(1, target_ports_len):
                    data = "%i:%i:%i:%i" % (
                        source_ports[0][0],
                        source_ports[0][1],
                        target_ports[i][0],
                        target_ports[i][1],
                    )
                    CanvasCallback(ACTION_PORTS_CONNECT, 0, 0, data)

    @pyqtSlot()
    def PortContextMenuDisconnect(self):
        try:
            connectionId = int(self.sender().data())
        except Exception:
            return

        CanvasCallback(ACTION_PORTS_DISCONNECT, connectionId, 0, "")

    @pyqtSlot(int, bool, int, int)
    def boxPositionChanged(self, groupId, split, x, y):
        x2 = y2 = 0

        target_group = None
        for group in canvas.group_list:
            if group.group_id == groupId:
                target_group = group
                if split and group.split:
                    pos = group.widgets[1].pos()
                    x2 = pos.x()
                    y2 = pos.y()
                break

        if target_group is not None and canvas.settings:
            try:
                if split:
                    canvas.settings.setValue(
                        "CanvasPositions/%s_OUTPUT" % target_group.group_name,
                        QPointF(x, y),
                    )
                else:
                    canvas.settings.setValue(
                        "CanvasPositions/%s" % target_group.group_name,
                        QPointF(x, y),
                    )
            except Exception:
                pass

        valueStr = "%i:%i:%i:%i" % (x, y, x2, y2)
        CanvasCallback(ACTION_GROUP_POSITION, groupId, 0, valueStr)

    @pyqtSlot(int, bool, int, int)
    def sboxPositionChanged(self, groupId, split, x2, y2):
        x = y = 0

        target_group = None
        for group in canvas.group_list:
            if group.group_id == groupId:
                target_group = group
                pos = group.widgets[0].pos()
                x = pos.x()
                y = pos.y()
                break

        if target_group is not None and canvas.settings:
            try:
                canvas.settings.setValue(
                    "CanvasPositions/%s_INPUT" % target_group.group_name,
                    QPointF(x2, y2),
                )
            except Exception:
                pass

        valueStr = "%i:%i:%i:%i" % (x, y, x2, y2)
        CanvasCallback(ACTION_GROUP_POSITION, groupId, 0, valueStr)


# ------------------------------------------------------------------------------------------------------------


def getStoredCanvasPosition(key, fallback_pos):
    try:
        return canvas.settings.value(
            "CanvasPositions/" + key, fallback_pos, type=QPointF
        )
    except Exception:
        return fallback_pos


def getStoredCanvasSplit(group_name, fallback_split_mode):
    try:
        return canvas.settings.value(
            "CanvasPositions/%s_SPLIT" % group_name, fallback_split_mode, type=int
        )
    except Exception:
        return fallback_split_mode


# ------------------------------------------------------------------------------------------------------------


def init(appName, scene, callback, debug=False):
    if debug:
        print(
            'PatchCanvas::init("%s", %s, %s, %s)'
            % (appName, scene, callback, bool2str(debug))
        )

    if canvas.initiated:
        qCritical("PatchCanvas::init() - already initiated")
        return

    if not callback:
        qFatal("PatchCanvas::init() - fatal error: callback not set")
        return

    canvas.callback = callback
    canvas.debug = debug
    canvas.scene = scene

    canvas.last_z_value = 0
    canvas.last_connection_id = 0
    canvas.initial_pos = QPointF(0, 0)
    canvas.size_rect = QRectF()

    if not canvas.qobject:
        canvas.qobject = CanvasObject()
    if not canvas.settings:
        canvas.settings = QSafeSettings("falkTX", appName)

    if canvas.theme:
        del canvas.theme
        canvas.theme = None

    for i in range(Theme.THEME_MAX):
        this_theme_name = getThemeName(i)
        if this_theme_name == options.theme_name:
            canvas.theme = Theme(i)
            break

    if not canvas.theme:
        canvas.theme = Theme(getDefaultTheme())

    canvas.scene.updateTheme()

    canvas.initiated = True


def clear():
    if canvas.debug:
        print("PatchCanvas::clear()")

    group_pos = {}
    group_list_ids = []
    port_list_ids = []
    connection_list_ids = []

    for group in canvas.group_list:
        group_pos[group.group_name] = (
            group.split,
            group.widgets[0].pos(),
            group.widgets[1].pos() if group.split else None,
        )
        group_list_ids.append(group.group_id)

    for port in canvas.port_list:
        port_list_ids.append((port.group_id, port.port_id))

    for connection in canvas.connection_list:
        connection_list_ids.append(connection.connection_id)

    for idx in connection_list_ids:
        disconnectPorts(idx)

    for group_id, port_id in port_list_ids:
        removePort(group_id, port_id)

    for idx in group_list_ids:
        removeGroup(idx)

    canvas.last_z_value = 0
    canvas.last_connection_id = 0

    canvas.group_list = []
    canvas.port_list = []
    canvas.connection_list = []
    canvas.group_plugin_map = {}
    canvas.old_group_pos = group_pos

    canvas.scene.clearSelection()

    # Cache custom colors across clear/refresh
    old_custom_colors = getattr(canvas, "old_custom_colors", {})
    for group in canvas.group_list:
        if group.widgets[0] and group.widgets[0].m_custom_color:
            old_custom_colors[group.group_name] = group.widgets[0].m_custom_color
    canvas.old_custom_colors = old_custom_colors

    animatedItems = []
    for animation in canvas.animation_list:
        animatedItems.append(animation.item())

    for item in canvas.scene.items():
        if (
            item.type() in (CanvasIconType, CanvasRubberbandType, CanvasContainerType)
            or item in animatedItems
        ):
            continue
        canvas.scene.removeItem(item)
        del item

    canvas.initiated = False

    QTimer.singleShot(0, canvas.scene.update)


# ------------------------------------------------------------------------------------------------------------


def setInitialPos(x, y):
    if canvas.debug:
        print("PatchCanvas::setInitialPos(%i, %i)" % (x, y))

    canvas.initial_pos.setX(x)
    canvas.initial_pos.setY(y)


def setCanvasSize(x, y, width, height):
    if canvas.debug:
        print("PatchCanvas::setCanvasSize(%i, %i, %i, %i)" % (x, y, width, height))

    canvas.size_rect.setX(x)
    canvas.size_rect.setY(y)
    canvas.size_rect.setWidth(width)
    canvas.size_rect.setHeight(height)
    canvas.scene.updateLimits()
    canvas.scene.fixScaleFactor()


def addGroup(
    group_id,
    group_name,
    split=SPLIT_UNDEF,
    icon=ICON_APPLICATION,
    pw_node_name=None,
):
    log_carla(f"patchcanvas.addGroup: group_id={group_id}, group_name='{group_name}'", level="debug")
    if canvas.debug:
        print(
            "PatchCanvas::addGroup(%i, %s, %s, %s)"
            % (group_id, group_name.encode(), split2str(split), icon2str(icon))
        )

    for group in canvas.group_list:
        if group.group_id == group_id:
            qWarning(
                "PatchCanvas::addGroup(%i, %s, %s, %s) - group already exists"
                % (group_id, group_name.encode(), split2str(split), icon2str(icon))
            )
            return None

    old_matching_group = canvas.old_group_pos.pop(group_name, None)

    if split == SPLIT_UNDEF:
        isHardware = bool(icon == ICON_HARDWARE)

        if features.handle_group_pos:
            split = getStoredCanvasSplit(group_name, SPLIT_YES if isHardware else split)
        elif isHardware:
            split = SPLIT_YES
        elif old_matching_group is not None and old_matching_group[0]:
            split = SPLIT_YES

    group_box = CanvasBox(group_id, group_name, icon, pw_node_name=pw_node_name)
    group_box.positionChanged.connect(canvas.qobject.boxPositionChanged)
    group_box.blockSignals(True)

    group_dict = group_dict_t()
    group_dict.group_id = group_id
    group_dict.group_name = group_name
    group_dict.pw_node_name = pw_node_name or group_name
    group_dict.split = bool(split == SPLIT_YES)
    group_dict.icon = icon
    group_dict.plugin_id = -1
    group_dict.plugin_ui = False
    group_dict.plugin_inline = False
    group_dict.widgets = [group_box, None]

    if split == SPLIT_YES:
        group_box.setSplit(True, PORT_MODE_OUTPUT)

        if features.handle_group_pos:
            group_box.setPos(
                getStoredCanvasPosition(
                    group_name + "_OUTPUT", CanvasGetNewGroupPos(False)
                )
            )
        elif old_matching_group is not None:
            group_box.setPos(old_matching_group[1])
        else:
            stored_pos = getStoredCanvasPosition(group_name + "_OUTPUT", None)
            if stored_pos is not None:
                group_box.setPos(stored_pos)
            else:
                group_box.setPos(CanvasGetNewGroupPos(False))

        group_sbox = CanvasBox(group_id, group_name, icon, pw_node_name=pw_node_name)
        group_sbox.positionChanged.connect(canvas.qobject.sboxPositionChanged)
        group_sbox.blockSignals(True)
        group_sbox.setSplit(True, PORT_MODE_INPUT)

        group_dict.widgets[1] = group_sbox

        if features.handle_group_pos:
            group_sbox.setPos(
                getStoredCanvasPosition(
                    group_name + "_INPUT", CanvasGetNewGroupPos(True)
                )
            )
        elif old_matching_group is not None and old_matching_group[0]:
            group_sbox.setPos(old_matching_group[2])
        else:
            stored_spos = getStoredCanvasPosition(group_name + "_INPUT", None)
            if stored_spos is not None:
                group_sbox.setPos(stored_spos)
            else:
                group_sbox.setPos(
                    group_box.x() + group_box.boundingRect().width() + 300, group_box.y()
                )

        canvas.last_z_value += 1
        group_sbox.setZValue(canvas.last_z_value)

        if options.eyecandy == EYECANDY_FULL and not options.auto_hide_groups:
            CanvasItemFX(group_sbox, True, False)

        group_sbox.checkItemPos()
        group_sbox.blockSignals(False)

    else:
        group_box.setSplit(False)

        if features.handle_group_pos:
            group_box.setPos(
                getStoredCanvasPosition(group_name, CanvasGetNewGroupPos(False))
            )
        elif old_matching_group is not None:
            group_box.setPos(old_matching_group[1])
        else:
            stored_pos = getStoredCanvasPosition(group_name, None)
            if stored_pos is not None:
                group_box.setPos(stored_pos)
            else:
                # Special ladish fake-split groups
                horizontal = bool(icon == ICON_HARDWARE or icon == ICON_LADISH_ROOM)
                group_box.setPos(CanvasGetNewGroupPos(horizontal))

    canvas.last_z_value += 1
    group_box.setZValue(canvas.last_z_value)

    group_box.checkItemPos()
    group_box.blockSignals(False)
    if hasattr(canvas, "old_custom_colors") and group_name in canvas.old_custom_colors:
        group_box.setCustomColor(canvas.old_custom_colors[group_name])
        if group_dict.split and group_dict.widgets[1]:
            group_dict.widgets[1].setCustomColor(canvas.old_custom_colors[group_name])

    canvas.group_list.append(group_dict)

    pending_ports = canvas.pending_ports.pop(group_id, None)
    if pending_ports:
        for port_id, port_name, port_mode, port_type, is_alternate in pending_ports:
            addPort(group_id, port_id, port_name, port_mode, port_type, is_alternate)

    if hasattr(canvas, "container_list"):
        for c in canvas.container_list:
            for desc in list(c.m_standby_descriptors):
                if c.matchesDescriptor(group_box, desc):
                    c.addItem(group_box)
                    break
            if group_dict.split and group_dict.widgets[1]:
                sbox = group_dict.widgets[1]
                for desc in list(c.m_standby_descriptors):
                    if c.matchesDescriptor(sbox, desc):
                        c.addItem(sbox)
                        break

    if options.eyecandy == EYECANDY_FULL and not options.auto_hide_groups:
        CanvasItemFX(group_box, True, False)
    else:
        QTimer.singleShot(0, canvas.scene.update)

    return group_dict


def removeGroup(group_id):
    if canvas.debug:
        print("PatchCanvas::removeGroup(%i)" % group_id)

    canvas.pending_ports.pop(group_id, None)

    for visual_group_id in tuple(canvas.pipewire_group_ids.pop(group_id, ())):
        canvas.pipewire_group_map = {
            key: value
            for key, value in canvas.pipewire_group_map.items()
            if value != visual_group_id
        }
        removeGroup(visual_group_id)

    for group in canvas.group_list:
        if group.group_id == group_id:
            item = group.widgets[0]
            group_name = group.group_name

            if group.split:
                s_item = group.widgets[1]

                if features.handle_group_pos:
                    canvas.settings.setValue(
                        "CanvasPositions/%s_OUTPUT" % group_name, item.pos()
                    )
                    canvas.settings.setValue(
                        "CanvasPositions/%s_INPUT" % group_name, s_item.pos()
                    )
                    canvas.settings.setValue(
                        "CanvasPositions/%s_SPLIT" % group_name, SPLIT_YES
                    )

                if hasattr(canvas, "container_list"):
                    for c in canvas.container_list:
                        if c.containsBox(s_item):
                            c.removeItem(s_item, to_standby=True)

                if options.eyecandy == EYECANDY_FULL:
                    CanvasItemFX(s_item, False, True)
                else:
                    s_item.removeIconFromScene()
                    canvas.scene.removeItem(s_item)
                    del s_item

            else:
                if features.handle_group_pos:
                    canvas.settings.setValue(
                        "CanvasPositions/%s" % group_name, item.pos()
                    )
                    canvas.settings.setValue(
                        "CanvasPositions/%s_SPLIT" % group_name, SPLIT_NO
                    )

            if hasattr(canvas, "container_list"):
                for c in canvas.container_list:
                    if c.containsBox(item):
                        c.removeItem(item, to_standby=True)

            if options.eyecandy == EYECANDY_FULL:
                CanvasItemFX(item, False, True)
            else:
                item.removeIconFromScene()
                canvas.scene.removeItem(item)
                del item

            canvas.group_list.remove(group)
            canvas.group_plugin_map.pop(group.plugin_id, None)

            QTimer.singleShot(0, canvas.scene.update)
            return

    qCritical(
        "PatchCanvas::removeGroup(%i) - unable to find group to remove" % group_id
    )


def renameGroup(group_id, new_group_name):
    if canvas.debug:
        print("PatchCanvas::renameGroup(%i, %s)" % (group_id, new_group_name.encode()))

    for group in canvas.group_list:
        if group.group_id == group_id:
            group.group_name = new_group_name
            group.widgets[0].setGroupName(new_group_name)

            if group.split and group.widgets[1]:
                group.widgets[1].setGroupName(new_group_name)

            QTimer.singleShot(0, canvas.scene.update)
            return

    qCritical(
        "PatchCanvas::renameGroup(%i, %s) - unable to find group to rename"
        % (group_id, new_group_name.encode())
    )


def splitGroup(group_id):
    if canvas.debug:
        print("PatchCanvas::splitGroup(%i)" % group_id)

    item = None
    group_name = ""
    group_icon = ICON_APPLICATION
    group_pos = None
    plugin_id = -1
    plugin_ui = False
    plugin_inline = False
    ports_data = []
    conns_data = []

    # Step 1 - Store all Item data
    for group in canvas.group_list:
        if group.group_id == group_id:
            if group.split:
                if canvas.debug:
                    print(
                        "PatchCanvas::splitGroup(%i) - group is already split"
                        % group_id
                    )
                return

            item = group.widgets[0]
            group_name = group.group_name
            group_icon = group.icon
            group_pos = item.pos()
            plugin_id = group.plugin_id
            plugin_ui = group.plugin_ui
            plugin_inline = group.plugin_inline
            break

    if not item:
        qCritical(
            "PatchCanvas::splitGroup(%i) - unable to find group to split" % group_id
        )
        return

    port_list_ids = list(item.getPortList())

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id in port_list_ids:
            port_dict = port_dict_t()
            port_dict.group_id = port.group_id
            port_dict.port_id = port.port_id
            port_dict.port_name = port.port_name
            port_dict.port_mode = port.port_mode
            port_dict.port_type = port.port_type
            port_dict.is_alternate = port.is_alternate
            port_dict.widget = None
            ports_data.append(port_dict)

    for connection in canvas.connection_list:
        if (
            connection.group_in_id == group_id
            and connection.port_in_id in port_list_ids
        ) or (
            connection.group_out_id == group_id
            and connection.port_out_id in port_list_ids
        ):
            connection_dict = connection_dict_t()
            connection_dict.connection_id = connection.connection_id
            connection_dict.group_in_id = connection.group_in_id
            connection_dict.port_in_id = connection.port_in_id
            connection_dict.group_out_id = connection.group_out_id
            connection_dict.port_out_id = connection.port_out_id
            connection_dict.widget = None
            conns_data.append(connection_dict)

    # Step 2 - Remove Item and Children
    for conn in conns_data:
        disconnectPorts(conn.connection_id)

    for port_id in port_list_ids:
        removePort(group_id, port_id)

    removeGroup(group_id)

    # Step 3 - Re-create Item, now split
    group = addGroup(group_id, group_name, SPLIT_YES, group_icon)

    if plugin_id >= 0:
        setGroupAsPlugin(group_id, plugin_id, plugin_ui, plugin_inline)

    for port in ports_data:
        addPort(
            group_id,
            port.port_id,
            port.port_name,
            port.port_mode,
            port.port_type,
            port.is_alternate,
        )

    for conn in conns_data:
        connectPorts(
            conn.connection_id,
            conn.group_out_id,
            conn.port_out_id,
            conn.group_in_id,
            conn.port_in_id,
            True,
        )

    if group is not None:
        group2_pos = QPointF(
            group_pos.x() + group.widgets[1].boundingRect().width() * 3 / 2,
            group_pos.y(),
        )
        group.widgets[0].blockSignals(True)
        group.widgets[0].setPos(group_pos)
        group.widgets[0].blockSignals(False)
        group.widgets[1].blockSignals(True)
        group.widgets[1].setPos(group2_pos)
        group.widgets[1].checkItemPos()
        group.widgets[1].blockSignals(False)
        valueStr = "%i:%i:%i:%i" % (
            group_pos.x(),
            group_pos.y(),
            group2_pos.x(),
            group2_pos.y(),
        )
        CanvasCallback(ACTION_GROUP_POSITION, group_id, 0, valueStr)

    QTimer.singleShot(0, canvas.scene.update)


def joinGroup(group_id):
    if canvas.debug:
        print("PatchCanvas::joinGroup(%i)" % group_id)

    item = None
    s_item = None
    group_name = ""
    group_icon = ICON_APPLICATION
    group_pos = None
    plugin_id = -1
    plugin_ui = False
    plugin_inline = False
    ports_data = []
    conns_data = []

    # Step 1 - Store all Item data
    for group in canvas.group_list:
        if group.group_id == group_id:
            if not group.split:
                if canvas.debug:
                    print("PatchCanvas::joinGroup(%i) - group is not split" % group_id)
                return

            item = group.widgets[0]
            s_item = group.widgets[1]
            group_name = group.group_name
            group_icon = group.icon
            group_pos = item.pos()
            plugin_id = group.plugin_id
            plugin_ui = group.plugin_ui
            plugin_inline = group.plugin_inline
            break

    # FIXME
    if not (item and s_item):
        qCritical(
            "PatchCanvas::joinGroup(%i) - unable to find groups to join" % group_id
        )
        return

    port_list_ids = list(item.getPortList())
    port_list_idss = s_item.getPortList()

    for port_id in port_list_idss:
        if port_id not in port_list_ids:
            port_list_ids.append(port_id)

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id in port_list_ids:
            port_dict = port_dict_t()
            port_dict.group_id = port.group_id
            port_dict.port_id = port.port_id
            port_dict.port_name = port.port_name
            port_dict.port_mode = port.port_mode
            port_dict.port_type = port.port_type
            port_dict.is_alternate = port.is_alternate
            port_dict.widget = None
            ports_data.append(port_dict)

    for connection in canvas.connection_list:
        if (
            connection.group_in_id == group_id
            and connection.port_in_id in port_list_ids
        ) or (
            connection.group_out_id == group_id
            and connection.port_out_id in port_list_ids
        ):
            connection_dict = connection_dict_t()
            connection_dict.connection_id = connection.connection_id
            connection_dict.group_in_id = connection.group_in_id
            connection_dict.port_in_id = connection.port_in_id
            connection_dict.group_out_id = connection.group_out_id
            connection_dict.port_out_id = connection.port_out_id
            connection_dict.widget = None
            conns_data.append(connection_dict)

    # Step 2 - Remove Item and Children
    for conn in conns_data:
        disconnectPorts(conn.connection_id)

    for port_id in port_list_ids:
        removePort(group_id, port_id)

    removeGroup(group_id)

    # Step 3 - Re-create Item, now together
    group = addGroup(group_id, group_name, SPLIT_NO, group_icon)

    if plugin_id >= 0:
        setGroupAsPlugin(group_id, plugin_id, plugin_ui, plugin_inline)

    for port in ports_data:
        addPort(
            group_id,
            port.port_id,
            port.port_name,
            port.port_mode,
            port.port_type,
            port.is_alternate,
        )

    for conn in conns_data:
        connectPorts(
            conn.connection_id,
            conn.group_out_id,
            conn.port_out_id,
            conn.group_in_id,
            conn.port_in_id,
            True,
        )

    if group is not None:
        group.widgets[0].blockSignals(True)
        group.widgets[0].setPos(group_pos)
        group.widgets[0].checkItemPos()
        group.widgets[0].blockSignals(False)
        valueStr = "%i:%i:%i:%i" % (group_pos.x(), group_pos.y(), 0, 0)
        CanvasCallback(ACTION_GROUP_POSITION, group_id, 0, valueStr)

    QTimer.singleShot(0, canvas.scene.update)


# ------------------------------------------------------------------------------------------------------------


def getGroupPos(group_id, port_mode=PORT_MODE_OUTPUT):
    if canvas.debug:
        print("PatchCanvas::getGroupPos(%i, %s)" % (group_id, port_mode2str(port_mode)))

    for group in canvas.group_list:
        if group.group_id == group_id:
            return group.widgets[
                1 if (group.split and port_mode == PORT_MODE_INPUT) else 0
            ].pos()

    qCritical(
        "PatchCanvas::getGroupPos(%i, %s) - unable to find group"
        % (group_id, port_mode2str(port_mode))
    )
    return QPointF(0, 0)


def saveGroupPositions():
    if canvas.debug:
        print("PatchCanvas::getGroupPositions()")

    ret = []

    for group in canvas.group_list:
        if group.split:
            pos1 = group.widgets[0].pos()
            pos2 = group.widgets[1].pos()
        else:
            pos1 = group.widgets[0].pos()
            pos2 = QPointF(0, 0)

        col_str = ""
        if group.widgets[0].m_custom_color:
            col_str = group.widgets[0].m_custom_color.name()

        hide_ports = getattr(group.widgets[0], "m_hide_unconnected_ports", False)

        # Port names per side, so a project skeleton can be drawn before plugins load.
        left_ports = []
        right_ports = []
        port_modes = {}
        port_types = {}
        for port in canvas.port_list:
            if port.group_id != group.group_id or port.widget is None:
                continue
            try:
                parent = port.widget.parentItem()
            except RuntimeError:
                continue
            if group.split and parent is group.widgets[1]:
                right_ports.append(port.port_name)
            else:
                left_ports.append(port.port_name)
            port_modes[port.port_name] = port.port_mode
            port_types[port.port_name] = port.port_type

        ret.append(
            {
                "name": group.group_name,
                "left": left_ports,
                "right": right_ports,
                "port_modes": port_modes,
                "port_types": port_types,
                "pos1x": pos1.x(),
                "pos1y": pos1.y(),
                "pos2x": pos2.x(),
                "pos2y": pos2.y(),
                "split": group.split,
                "color": col_str,
                "hide_unconnected_ports": hide_ports,
                "width": group.widgets[0].p_width,
                "height": group.widgets[0].p_height,
            }
        )

    return ret


def restoreGroupPositions(dataList):
    if canvas.debug:
        print("PatchCanvas::restoreGroupPositions(...)")

    mapping = {}

    for group in canvas.group_list:
        mapping[group.group_name] = group

    for data in dataList:
        name = data["name"]
        group = mapping.get(name, None)

        if group is None:
            continue

        group.widgets[0].blockSignals(True)
        group.widgets[0].setPos(data["pos1x"], data["pos1y"])
        group.widgets[0].blockSignals(False)

        if group.split and group.widgets[1]:
            group.widgets[1].blockSignals(True)
            group.widgets[1].setPos(data["pos2x"], data["pos2y"])
            group.widgets[1].blockSignals(False)

        # Restore saved node color (unless overridden by mapped rack plugin)
        saved_node_color = data.get("color")
        if saved_node_color and getattr(group, "plugin_id", -1) < 0:
            group.widgets[0].setCustomColor(saved_node_color, notify=False)
            if group.split and group.widgets[1]:
                group.widgets[1].setCustomColor(saved_node_color, notify=False)

        # Restore hide_unconnected_ports state
        if data.get("hide_unconnected_ports"):
            group.widgets[0]._saved_hide_unconnected_ports = True
            if group.split and group.widgets[1]:
                group.widgets[1]._saved_hide_unconnected_ports = True

    # Defer applying hide_unconnected_ports until all backend connections have finished linking
    def _apply_deferred_hide_ports():
        for grp in canvas.group_list:
            for w in grp.widgets:
                if w and getattr(w, "_saved_hide_unconnected_ports", False):
                    delattr(w, "_saved_hide_unconnected_ports")
                    if hasattr(w, "setHideUnconnectedPorts"):
                        w.setHideUnconnectedPorts(True)
                    else:
                        w.m_hide_unconnected_ports = True
                        if hasattr(w, "updatePositions"):
                            w.updatePositions()
        # Ensure all existing cables sync their geometries to newly shifted port positions
        for conn in canvas.connection_list:
            if hasattr(conn, "widget") and conn.widget:
                conn.widget.updateLinePos()
        if hasattr(canvas, "scene") and canvas.scene:
            canvas.scene.zoom_fit()
            canvas.scene.update()

    QTimer.singleShot(150, _apply_deferred_hide_ports)

    if hasattr(canvas, "scene") and canvas.scene:
        canvas.scene.update()


def setGroupPos(group_id, group_pos_x, group_pos_y):
    setGroupPosFull(group_id, group_pos_x, group_pos_y, group_pos_x, group_pos_y)


def setGroupPosFull(
    group_id, group_pos_x_o, group_pos_y_o, group_pos_x_i, group_pos_y_i
):
    if canvas.debug:
        print(
            "PatchCanvas::setGroupPos(%i, %i, %i, %i, %i)"
            % (group_id, group_pos_x_o, group_pos_y_o, group_pos_x_i, group_pos_y_i)
        )

    for group in canvas.group_list:
        if group.group_id == group_id:
            group.widgets[0].blockSignals(True)
            group.widgets[0].setPos(group_pos_x_o, group_pos_y_o)
            group.widgets[0].checkItemPos()
            group.widgets[0].blockSignals(False)

            if group.split and group.widgets[1]:
                group.widgets[1].blockSignals(True)
                group.widgets[1].setPos(group_pos_x_i, group_pos_y_i)
                group.widgets[1].checkItemPos()
                group.widgets[1].blockSignals(False)

            QTimer.singleShot(0, canvas.scene.update)
            return

    qCritical(
        "PatchCanvas::setGroupPos(%i, %i, %i, %i, %i) - unable to find group to reposition"
        % (group_id, group_pos_x_o, group_pos_y_o, group_pos_x_i, group_pos_y_i)
    )


# ------------------------------------------------------------------------------------------------------------


def setGroupIcon(group_id, icon):
    if canvas.debug:
        print("PatchCanvas::setGroupIcon(%i, %s)" % (group_id, icon2str(icon)))

    for group in canvas.group_list:
        if group.group_id == group_id:
            group.icon = icon
            group.widgets[0].setIcon(icon)

            if group.split and group.widgets[1]:
                group.widgets[1].setIcon(icon)

            QTimer.singleShot(0, canvas.scene.update)
            return

    qCritical(
        "PatchCanvas::setGroupIcon(%i, %s) - unable to find group to change icon"
        % (group_id, icon2str(icon))
    )


def setGroupAsPlugin(group_id, plugin_id, hasUI, hasInlineDisplay):
    if canvas.debug:
        print(
            "PatchCanvas::setGroupAsPlugin(%i, %i, %s, %s)"
            % (group_id, plugin_id, bool2str(hasUI), bool2str(hasInlineDisplay))
        )

    for group in canvas.group_list:
        if group.group_id == group_id:
            group.plugin_id = plugin_id
            group.plugin_ui = hasUI
            group.plugin_inline = hasInlineDisplay
            group.widgets[0].setAsPlugin(plugin_id, hasUI, hasInlineDisplay)

            if group.split and group.widgets[1]:
                group.widgets[1].setAsPlugin(plugin_id, hasUI, hasInlineDisplay)

            # Sync saved custom color if present
            try:
                from carla_shared import gCarla, CUSTOM_DATA_TYPE_PROPERTY
                from carla_backend import MAIN_CARLA_PLUGIN_ID
                pitem = gCarla.gui.getPluginItem(plugin_id) if (hasattr(gCarla.gui, "getPluginItem") and plugin_id != MAIN_CARLA_PLUGIN_ID) else None
                saved_color = (
                    gCarla.gui.host.get_custom_data_value(
                        plugin_id, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
                    )
                    if (hasattr(gCarla.gui, "host") and plugin_id != MAIN_CARLA_PLUGIN_ID and plugin_id < getattr(gCarla.gui.host, "get_plugin_count", lambda: 0)())
                    else None
                )
                hex_col = None
                if saved_color and saved_color != "255;255;255":
                    parts = tuple(int(i) for i in saved_color.split(";", 3))
                    if parts != (255, 255, 255):
                        hex_col = f"#{parts[0]:02x}{parts[1]:02x}{parts[2]:02x}"
                elif pitem is not None and pitem.fOptions.get("color") is not None:
                    c = pitem.fOptions["color"]
                    if c != (255, 255, 255) and c != (40, 40, 40):
                        hex_col = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"

                if hex_col:
                    group.widgets[0].setCustomColor(hex_col, notify=False)
                    if group.split and group.widgets[1]:
                        group.widgets[1].setCustomColor(hex_col, notify=False)
            except Exception:
                pass

            canvas.group_plugin_map[plugin_id] = group

            if hasattr(canvas, "container_list"):
                for c in canvas.container_list:
                    for desc in list(c.m_standby_descriptors):
                        if c.matchesDescriptor(group.widgets[0], desc):
                            c.addItem(group.widgets[0])
                            break
                    if group.split and group.widgets[1]:
                        for desc in list(c.m_standby_descriptors):
                            if c.matchesDescriptor(group.widgets[1], desc):
                                c.addItem(group.widgets[1])
                                break
            return

    qCritical(
        "PatchCanvas::setGroupAsPlugin(%i, %i, %s, %s) - unable to find group to set as plugin"
        % (group_id, plugin_id, bool2str(hasUI), bool2str(hasInlineDisplay))
    )


# ------------------------------------------------------------------------------------------------------------


def focusGroupUsingPluginId(plugin_id):
    if canvas.debug:
        print("PatchCanvas::focusGroupUsingPluginId(%i)" % (plugin_id,))

    if plugin_id < 0 or plugin_id >= MAX_PLUGIN_ID_ALLOWED:
        return False

    for group in canvas.group_list:
        if group.plugin_id == plugin_id:
            item = group.widgets[0]
            canvas.scene.clearSelection()
            view = canvas.scene.getView()
            if hasattr(view, "animateFocusOn"):
                view.animateFocusOn(item)
            else:
                view.centerOn(item)
            item.setSelected(True)
            return True


def focusGroupUsingGroupName(group_name):
    if canvas.debug:
        print("PatchCanvas::focusGroupUsingGroupName(%s)" % (group_name,))

    for group in canvas.group_list:
        if group.group_name == group_name:
            item = group.widgets[0]
            canvas.scene.clearSelection()
            view = canvas.scene.getView()
            if hasattr(view, "animateFocusOn"):
                view.animateFocusOn(item)
            else:
                view.centerOn(item)
            item.setSelected(True)
            return True


# ------------------------------------------------------------------------------------------------------------


def addPort(group_id, port_id, port_name, port_mode, port_type, is_alternate=False):
    if canvas.debug:
        print(
            "PatchCanvas::addPort(%i, %i, %s, %s, %s, %s)"
            % (
                group_id,
                port_id,
                port_name.encode(),
                port_mode2str(port_mode),
                port_type2str(port_type),
                bool2str(is_alternate),
            )
        )

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id == port_id:
            qWarning(
                "PatchCanvas::addPort(%i, %i, %s, %s, %s) - port already exists"
                % (
                    group_id,
                    port_id,
                    port_name.encode(),
                    port_mode2str(port_mode),
                    port_type2str(port_type),
                )
            )
            return

    source_group = None
    for group in canvas.group_list:
        if group.group_id == group_id:
            source_group = group
            break

    if source_group is None:
        # Ports can arrive before their client group (or while the canvas is being
        # rebuilt). Keep them and replay them when the group shows up.
        pending = canvas.pending_ports.setdefault(group_id, [])
        if not any(entry[0] == port_id for entry in pending):
            pending.append((port_id, port_name, port_mode, port_type, is_alternate))
        log_carla(
            f"patchcanvas.addPort: queued port {port_id} for not-yet-known group {group_id}",
            level="debug",
        )
        return

    for port in canvas.port_list:
        if port.group_id != group_id or port.port_name != port_name:
            continue
        if getattr(port, "port_id", 0) < 0:
            old_port_id = port.port_id
            port.port_id = port_id
            port.port_name = port_name
            port.port_mode = port_mode
            port.port_type = port_type
            port.is_alternate = is_alternate
            port_dict = getattr(port.widget, "_port_dict", None)
            if port_dict is not None:
                port_dict.port_id = port_id
                port_dict.port_name = port_name
                port_dict.port_mode = port_mode
                port_dict.port_type = port_type
                port_dict.is_alternate = is_alternate
            if hasattr(port.widget, "setPortMode"):
                port.widget.setPortMode(port_mode)
            if hasattr(port.widget, "m_port_type"):
                port.widget.m_port_type = port_type
            target_parent = source_group.widgets[0]
            if source_group.split and source_group.widgets[1] is not None and port_mode == PORT_MODE_INPUT:
                target_parent = source_group.widgets[1]
            old_parent = port.widget.parentItem()
            if old_parent is not None and target_parent is not None and old_parent is not target_parent:
                if hasattr(old_parent, "m_port_list_ids") and old_port_id in old_parent.m_port_list_ids:
                    old_parent.m_port_list_ids.remove(old_port_id)
                port.widget.setParentItem(target_parent)
                if old_port_id not in target_parent.m_port_list_ids:
                    target_parent.m_port_list_ids.append(old_port_id)
                old_parent.updatePositions()
                target_parent.updatePositions()
            elif old_parent is not None:
                old_parent.updatePositions()
            for conn in canvas.connection_list:
                if conn.group_out_id == group_id and conn.port_out_id == old_port_id:
                    conn.port_out_id = port_id
                if conn.group_in_id == group_id and conn.port_in_id == old_port_id:
                    conn.port_in_id = port_id
            return

    display_name = CanvasGetPortDisplayName(source_group.group_name, port_name)
    visual_group_id = group_id
    log_carla(
        f"patchcanvas.addPort: group_id={group_id} ('{source_group.group_name}'), port_id={port_id}, port_name='{port_name}', display_name='{display_name}'",
        level="debug"
    )

    if display_name != port_name:
        stream_key = (group_id, display_name)
        visual_group_id = canvas.pipewire_group_map.get(stream_key)
        if visual_group_id is None:
            visual_group_id = canvas.next_pipewire_group_id
            canvas.next_pipewire_group_id -= 1
            canvas.pipewire_group_map[stream_key] = visual_group_id
            canvas.pipewire_group_ids.setdefault(group_id, set()).add(visual_group_id)
            source_pw_name = (
                getattr(source_group, "pw_node_name", None)
                or source_group.group_name
            )
            addGroup(
                visual_group_id,
                display_name,
                SPLIT_YES if source_group.split else SPLIT_NO,
                source_group.icon,
                pw_node_name=source_pw_name,
            )

    box_widget = None
    port_widget = None

    for group in canvas.group_list:
        if group.group_id == visual_group_id:
            if (
                group.split
                and group.widgets[0].getSplitMode() != port_mode
                and group.widgets[1]
            ):
                n = 1
            else:
                n = 0
            box_widget = group.widgets[n]
            if box_widget:
                source_pw_name = (
                    getattr(source_group, "pw_node_name", None)
                    or source_group.group_name
                )
                if source_pw_name and (
                    not getattr(box_widget, "pw_node_name", None)
                    or box_widget.pw_node_name == box_widget.m_group_name
                ):
                    box_widget.pw_node_name = source_pw_name
            port_widget = box_widget.addPortFromGroup(
                port_id, port_mode, port_type, port_name, is_alternate, group_id
            )
            break

    if not (box_widget and port_widget):
        qCritical(
            "PatchCanvas::addPort(%i, %i, %s, %s, %s) - Unable to find parent group"
            % (
                group_id,
                port_id,
                port_name.encode(),
                port_mode2str(port_mode),
                port_type2str(port_type),
            )
        )
        return

    port_dict = port_dict_t()
    port_dict.group_id = group_id
    port_dict.port_id = port_id
    port_dict.port_name = port_name
    port_dict.port_mode = port_mode
    port_dict.port_type = port_type
    port_dict.is_alternate = is_alternate
    port_dict.widget = port_widget
    canvas.port_list.append(port_dict)

    box_widget.updatePositions()

    if options.eyecandy == EYECANDY_FULL:
        CanvasItemFX(port_widget, True, False)

    QTimer.singleShot(0, canvas.scene.update)


def removePort(group_id, port_id):
    if canvas.debug:
        print("PatchCanvas::removePort(%i, %i)" % (group_id, port_id))

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id == port_id:
            item = port.widget
            try:
                pitem = item.parentItem()
                canvas.scene.removeItem(item)
            except RuntimeError:
                pass
            else:
                pitem.removePortFromGroup(port_id)
            canvas.port_list.remove(port)
            del item

            visual_group = pitem
            if visual_group.m_group_id < 0 and not visual_group.m_port_list_ids:
                for key, value in tuple(canvas.pipewire_group_map.items()):
                    if value == visual_group.m_group_id:
                        del canvas.pipewire_group_map[key]
                        break
                removeGroup(visual_group.m_group_id)

            QTimer.singleShot(0, canvas.scene.update)
            return

    qCritical(
        "PatchCanvas::removePort(%i, %i) - Unable to find port to remove"
        % (group_id, port_id)
    )


def renamePort(group_id, port_id, new_port_name):
    if canvas.debug:
        print(
            "PatchCanvas::renamePort(%i, %i, %s)"
            % (group_id, port_id, new_port_name.encode())
        )

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id == port_id:
            port.port_name = new_port_name
            port.widget.setPortName(new_port_name)
            port.widget.parentItem().updatePositions()

            QTimer.singleShot(0, canvas.scene.update)
            return

    qCritical(
        "PatchCanvas::renamePort(%i, %i, %s) - Unable to find port to rename"
        % (group_id, port_id, new_port_name.encode())
    )


def connectPorts(
    connection_id,
    group_out_id,
    port_out_id,
    group_in_id,
    port_in_id,
    fromSplitOrJoin=False,
):
    if canvas.last_connection_id >= connection_id and not fromSplitOrJoin:
        print(
            "PatchCanvas::connectPorts(%i, %i, %i, %i, %i) - invalid connection id received (last: %i)"
            % (
                connection_id,
                group_out_id,
                port_out_id,
                group_in_id,
                port_in_id,
                canvas.last_connection_id,
            )
        )
        return

    canvas.last_connection_id = connection_id

    if canvas.debug:
        print(
            "PatchCanvas::connectPorts(%i, %i, %i, %i, %i)"
            % (connection_id, group_out_id, port_out_id, group_in_id, port_in_id)
        )

    port_out = None
    port_in = None
    port_out_parent = None
    port_in_parent = None

    for port in canvas.port_list:
        if port.group_id == group_out_id and port.port_id == port_out_id:
            port_out = port.widget
            port_out_parent = port_out.parentItem()
        elif port.group_id == group_in_id and port.port_id == port_in_id:
            port_in = port.widget
            port_in_parent = port_in.parentItem()

    # FIXME
    if not (port_out and port_in):
        qCritical(
            "PatchCanvas::connectPorts(%i, %i, %i, %i, %i) - unable to find ports to connect"
            % (connection_id, group_out_id, port_out_id, group_in_id, port_in_id)
        )
        return

    connection_dict = connection_dict_t()
    connection_dict.connection_id = connection_id
    connection_dict.group_in_id = group_in_id
    connection_dict.port_in_id = port_in_id
    connection_dict.group_out_id = group_out_id
    connection_dict.port_out_id = port_out_id

    line_shape = resolve_line_algorithm().name
    line_stroke = getattr(options, "line_stroke", "solid")
    line_opacity = getattr(options, "line_opacity", 100)
    connection_dict.widget = CanvasLine(
        port_out, port_in, None,
        shape=line_shape, stroke=line_stroke, opacity=line_opacity
    )

    canvas.scene.addItem(connection_dict.widget)

    port_out_parent.addLineFromGroup(connection_dict.widget, connection_id)
    port_in_parent.addLineFromGroup(connection_dict.widget, connection_id)

    canvas.last_z_value += 1
    port_out_parent.setZValue(canvas.last_z_value)
    port_in_parent.setZValue(canvas.last_z_value)

    canvas.last_z_value += 1
    connection_dict.widget.setZValue(canvas.last_z_value)

    canvas.connection_list.append(connection_dict)

    # When hide_unconnected_ports is active, connecting a port reveals it and reshapes the box
    if getattr(port_out_parent, "m_hide_unconnected_ports", False):
        port_out_parent.updatePositions()
    if getattr(port_in_parent, "m_hide_unconnected_ports", False):
        port_in_parent.updatePositions()

    connection_dict.widget.updateLinePos()
    log_carla(
        f"patchcanvas.connectPorts: id={connection_id}, {group_out_id}:{port_out_id} -> {group_in_id}:{port_in_id}",
        level="debug"
    )

    if options.eyecandy == EYECANDY_FULL:
        item = connection_dict.widget
        # New connections appear instantly, no fade-in delay
        CanvasItemFX(item, True, False, duration=0)

    canvas.scene.update()
    QTimer.singleShot(0, canvas.scene.update)


def disconnectPorts(connection_id):
    log_carla(f"patchcanvas.disconnectPorts: id={connection_id}", level="debug")
    if canvas.debug:
        print("PatchCanvas::disconnectPorts(%i)" % connection_id)

    line = None
    item1 = None
    item2 = None
    group1id = port1id = 0
    group2id = port2id = 0

    for connection in canvas.connection_list:
        if connection.connection_id == connection_id:
            group1id = connection.group_out_id
            group2id = connection.group_in_id
            port1id = connection.port_out_id
            port2id = connection.port_in_id
            line = connection.widget
            canvas.connection_list.remove(connection)
            break

    if not line:
        qCritical(
            "PatchCanvas::disconnectPorts(%i) - unable to find connection ports"
            % connection_id
        )
        return

    for port in canvas.port_list:
        if port.group_id == group1id and port.port_id == port1id:
            item1 = port.widget
            break

    if not item1:
        qCritical(
            "PatchCanvas::disconnectPorts(%i) - unable to find output port"
            % connection_id
        )
        return

    for port in canvas.port_list:
        if port.group_id == group2id and port.port_id == port2id:
            item2 = port.widget
            break

    if not item2:
        qCritical(
            "PatchCanvas::disconnectPorts(%i) - unable to find input port"
            % connection_id
        )
        return

    item1p = item1.parentItem()
    item2p = item2.parentItem()
    if item1p:
        item1p.removeLineFromGroup(connection_id)
    if item2p:
        item2p.removeLineFromGroup(connection_id)

    if options.eyecandy == EYECANDY_FULL:
        CanvasItemFX(line, False, True)
        return

    canvas.scene.removeItem(line)
    del line

    QTimer.singleShot(0, canvas.scene.update)


# ------------------------------------------------------------------------------------------------------------


def autoArrange():
    """
    Arranges canvas nodes according to left-to-right audio/MIDI signal flow:
      1. Anchors connected Hardware Capture to Layer 0 (leftmost).
      2. Computes topological layers for connected nodes (resolving feedback loops).
      3. Anchors connected Hardware Playback to the final layer (rightmost).
      4. Detects exclusive 1-to-1 relationships and locks them to the exact same Y
         coordinate across consecutive columns (side-by-side horizontal tracks).
      5. Resolves intra-column overlaps while maintaining strand Y-alignment.
      6. Centers single fan-in/fan-out nodes across the tracks they feed or receive from.
      7. Centers isolated/unconnected nodes in rows below the active graph.
    """
    log_carla("PatchCanvas::autoArrange() started")
    if canvas.debug:
        print("PatchCanvas::autoArrange()")

    node_gap = 64
    vertical_gap = 40
    max_isolated_per_row = 5

    nodes = []
    port_nodes = {}
    node_to_group = {}

    # Gather active widgets and map ports to their parent box widget
    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is None or not widget.m_port_list_ids:
                continue
            nodes.append(widget)
            node_to_group[widget] = group
            for port in canvas.port_list:
                if port.widget and port.widget.parentItem() == widget:
                    port_nodes[(port.group_id, port.port_id)] = widget

    if not nodes:
        return

    node_set = set(nodes)
    edges = {node: set() for node in nodes}
    incoming = {node: set() for node in nodes}
    edge_weight = {}

    # Build directed graph edges from active connections
    for connection in canvas.connection_list:
        source = port_nodes.get((connection.group_out_id, connection.port_out_id))
        target = port_nodes.get((connection.group_in_id, connection.port_in_id))
        if source in node_set and target in node_set and source != target:
            edges[source].add(target)
            incoming[target].add(source)
            edge_weight[(source, target)] = edge_weight.get((source, target), 0) + 1

    connected = [node for node in nodes if edges[node] or incoming[node]]
    isolated = [node for node in nodes if node not in connected]

    # --- 1. CONNECTED GRAPH LAYOUT ---
    if connected:
        # Detect and temporarily ignore feedback back-edges (DFS cycle-breaking)
        dag_edges = {node: set() for node in connected}
        state = {node: 0 for node in connected}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(u):
            state[u] = 1
            for v in sorted(edges[u], key=lambda n: node_to_group[n].group_name):
                if state[v] == 1:
                    continue  # feedback loop / back-edge ignored for horizontal layering
                dag_edges[u].add(v)
                if state[v] == 0:
                    dfs(v)
            state[u] = 2

        # Visit true sources first (preferring hardware capture)
        sources_priority = sorted(
            connected,
            key=lambda n: (
                0
                if (node_to_group[n].icon == ICON_HARDWARE and not incoming[n])
                else (1 if not incoming[n] else 2),
                node_to_group[n].group_name,
            ),
        )
        for node in sources_priority:
            if state[node] == 0:
                dfs(node)

        dag_incoming = {node: set() for node in connected}
        for u in connected:
            for v in dag_edges[u]:
                dag_incoming[v].add(u)

        # Topological sorting (Kahn's algorithm)
        in_degree = {node: len(dag_incoming[node]) for node in connected}
        queue = [n for n in connected if in_degree[n] == 0]
        if not queue:
            queue = [connected[0]]
            in_degree[connected[0]] = 0

        topo_order = []
        while queue:
            u = queue.pop(0)
            topo_order.append(u)
            for v in sorted(dag_edges[u], key=lambda n: node_to_group[n].group_name):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        for n in connected:
            if n not in topo_order:
                topo_order.append(n)

        # Longest-path layer computation
        layers = {node: 0 for node in connected}
        for u in topo_order:
            for v in dag_edges[u]:
                layers[v] = max(layers[v], layers[u] + 1)

        # Anchor connected hardware capture to Layer 0
        for n in connected:
            if node_to_group[n].icon == ICON_HARDWARE and not incoming[n]:
                layers[n] = 0

        # Anchor connected hardware playback (pure sinks) to outermost right column
        hw_playback = [
            n
            for n in connected
            if node_to_group[n].icon == ICON_HARDWARE and not edges[n]
        ]
        if hw_playback:
            max_other = max(
                (layers[n] for n in connected if n not in hw_playback), default=0
            )
            target_hw_layer = max_other + 1
            for n in hw_playback:
                layers[n] = target_hw_layer

        # --- 2. EXCLUSIVE 1-TO-1 STRAND EXTRACTION ---
        exclusive_next = {}
        exclusive_prev = {}
        for u in connected:
            if len(edges[u]) == 1:
                v = next(iter(edges[u]))
                if len(incoming[v]) == 1 and next(iter(incoming[v])) == u:
                    exclusive_next[u] = v
                    exclusive_prev[v] = u

        # Build strands (maximal 1-to-1 linear chains)
        strands = []
        visited_strand = set()
        node_to_strand = {}

        for u in connected:
            if u in visited_strand:
                continue
            head = u
            while head in exclusive_prev:
                head = exclusive_prev[head]
            strand = []
            curr = head
            while curr:
                strand.append(curr)
                visited_strand.add(curr)
                curr = exclusive_next.get(curr)
            strands.append(strand)
            for n in strand:
                node_to_strand[n] = strand

        # Group nodes into columns
        columns = {}
        for n in connected:
            columns.setdefault(layers[n], []).append(n)
        sorted_layers = sorted(columns.keys())

        # Establish initial vertical rank for strands
        initial_sorted = sorted(strands, key=lambda s: (
            0 if node_to_group[s[0]].icon == ICON_HARDWARE else 1,
            layers[s[0]],
            node_to_group[s[0]].group_name,
            id(s)
        ))
        
        strand_idx = {id(s): i for i, s in enumerate(initial_sorted)}
        
        # Barycenter heuristic: minimize line crossings by sorting strands based on their connections
        for _ in range(8):
            new_idx = {}
            for s in initial_sorted:
                sid = id(s)
                head = s[0]
                tail = s[-1]
                weighted_sum = 0
                total_weight = 0
                
                # Incoming to head
                for u in dag_incoming[head]:
                    w = edge_weight.get((u, head), 1)
                    weighted_sum += strand_idx[id(node_to_strand[u])] * w
                    total_weight += w
                
                # Outgoing from tail
                for v in dag_edges[tail]:
                    w = edge_weight.get((tail, v), 1)
                    weighted_sum += strand_idx[id(node_to_strand[v])] * w
                    total_weight += w
                
                if total_weight > 0:
                    new_idx[sid] = weighted_sum / total_weight
                else:
                    new_idx[sid] = strand_idx[sid]
            
            initial_sorted.sort(key=lambda s: new_idx[id(s)])
            for i, s in enumerate(initial_sorted):
                strand_idx[id(s)] = i

        strand_rank = {}
        for s in strands:
            strand_rank[id(s)] = strand_idx[id(s)]

        # Sort nodes within each column by their strand's rank
        for layer in sorted_layers:
            col = columns[layer]
            col.sort(key=lambda n: strand_rank[id(node_to_strand[n])])

        # Assign unified Y coordinates per strand to ensure side-by-side alignment
        strand_y = {id(s): 0.0 for s in strands}

        # Iteratively propagate clearance constraints across all columns
        num_passes = len(columns) + 2
        for _ in range(num_passes):
            for layer in sorted_layers:
                col = columns[layer]
                for i in range(1, len(col)):
                    prev_node = col[i - 1]
                    curr_node = col[i]
                    prev_strand = node_to_strand[prev_node]
                    curr_strand = node_to_strand[curr_node]

                    required_y = (
                        strand_y[id(prev_strand)]
                        + prev_node.boundingRect().height()
                        + vertical_gap
                    )
                    if strand_y[id(curr_strand)] < required_y:
                        strand_y[id(curr_strand)] = required_y

        # Apply locked Y position to all nodes in each strand
        for s in strands:
            base_y = strand_y[id(s)]
            for n in s:
                n.setPos(n.x(), base_y)

        # Vertically center single fan-in / fan-out nodes (e.g. Master out or Capture in)
        for layer in sorted_layers:
            col = columns[layer]
            for idx, n in enumerate(col):
                s = node_to_strand[n]
                if len(s) == 1:
                    # Pure source feeding multiple outputs: center between targets
                    if edges[n] and not incoming[n]:
                        avg_y = sum(
                            c.y()
                            + (c.boundingRect().height() - n.boundingRect().height())
                            / 2.0
                            for c in edges[n]
                        ) / len(edges[n])
                        min_y = (
                            (
                                col[idx - 1].y()
                                + col[idx - 1].boundingRect().height()
                                + vertical_gap
                            )
                            if idx > 0
                            else 0
                        )
                        max_y = (
                            (
                                col[idx + 1].y()
                                - n.boundingRect().height()
                                - vertical_gap
                            )
                            if idx < len(col) - 1
                            else float("inf")
                        )
                        if min_y <= max_y:
                            clamped_y = max(min_y, min(max_y, avg_y))
                            n.setPos(n.x(), clamped_y)

                    # Pure sink receiving from multiple inputs: center between sources
                    elif incoming[n] and not edges[n]:
                        avg_y = sum(
                            p.y()
                            + (p.boundingRect().height() - n.boundingRect().height())
                            / 2.0
                            for p in incoming[n]
                        ) / len(incoming[n])
                        min_y = (
                            (
                                col[idx - 1].y()
                                + col[idx - 1].boundingRect().height()
                                + vertical_gap
                            )
                            if idx > 0
                            else 0
                        )
                        max_y = (
                            (
                                col[idx + 1].y()
                                - n.boundingRect().height()
                                - vertical_gap
                            )
                            if idx < len(col) - 1
                            else float("inf")
                        )
                        if min_y <= max_y:
                            clamped_y = max(min_y, min(max_y, avg_y))
                            n.setPos(n.x(), clamped_y)

        # Assign X coordinates with dynamic column widths
        current_x = 0
        for layer in sorted_layers:
            col = columns[layer]
            col_width = max(n.boundingRect().width() for n in col)
            for n in col:
                n.setPos(current_x, n.y())
            current_x += col_width + node_gap

    # --- 3. ISOLATED NODES LAYOUT ---
    if isolated:
        isolated.sort(
            key=lambda n: (
                0 if node_to_group[n].icon == ICON_HARDWARE else 1,
                node_to_group[n].group_name,
            )
        )

        if connected:
            conn_min_x = min(n.x() for n in connected)
            conn_max_x = max(n.x() + n.boundingRect().width() for n in connected)
            conn_width = conn_max_x - conn_min_x
            conn_max_y = max(n.y() + n.boundingRect().height() for n in connected)
            start_y = conn_max_y + vertical_gap * 1.5
        else:
            conn_min_x = 0
            conn_width = 800
            start_y = 0

        # Pack into rows
        rows = []
        curr_row = []
        for n in isolated:
            curr_row.append(n)
            if len(curr_row) >= max_isolated_per_row:
                rows.append(curr_row)
                curr_row = []
        if curr_row:
            rows.append(curr_row)

        curr_y = start_y
        for row in rows:
            row_width = (
                sum(n.boundingRect().width() for n in row) + (len(row) - 1) * node_gap
            )
            if connected and conn_width > row_width:
                row_start_x = conn_min_x + (conn_width - row_width) / 2.0
            else:
                row_start_x = conn_min_x

            rx = row_start_x
            row_max_h = max(n.boundingRect().height() for n in row)
            for n in row:
                n.setPos(rx, curr_y)
                rx += n.boundingRect().width() + node_gap
            curr_y += row_max_h + vertical_gap

    # --- 4. CENTER NODES IN PATCHCANVAS ---
    min_x = min(n.x() for n in nodes)
    min_y = min(n.y() for n in nodes)
    max_x = max(n.x() + n.boundingRect().width() for n in nodes)
    max_y = max(n.y() + n.boundingRect().height() for n in nodes)

    bbox_w = max_x - min_x
    bbox_h = max_y - min_y

    canvas_w = (
        canvas.size_rect.width()
        if not canvas.size_rect.isNull()
        else (canvas.scene.width() if canvas.scene else 0)
    )
    canvas_h = (
        canvas.size_rect.height()
        if not canvas.size_rect.isNull()
        else (canvas.scene.height() if canvas.scene else 0)
    )
    canvas_x = canvas.size_rect.x() if not canvas.size_rect.isNull() else 0
    canvas_y = canvas.size_rect.y() if not canvas.size_rect.isNull() else 0

    if canvas_w > 0 and canvas_h > 0:
        target_x = canvas_x + (canvas_w - bbox_w) / 2.0
        target_y = canvas_y + (canvas_h - bbox_h) / 2.0
        target_x = max(canvas_x, target_x)
        target_y = max(canvas_y, target_y)
        offset_x = target_x - min_x
        offset_y = target_y - min_y
    else:
        offset_x = 40 - min_x
        offset_y = 40 - min_y

    for node in nodes:
        node.blockSignals(True)
        node.setPos(node.x() + offset_x, node.y() + offset_y)
        node.checkItemPos()
        node.blockSignals(False)

    # Sync updated positions with Carla host / settings
    for group in canvas.group_list:
        pos1 = group.widgets[0].pos()
        pos2 = (
            group.widgets[1].pos()
            if group.split and group.widgets[1]
            else QPointF(0, 0)
        )
        valueStr = "%i:%i:%i:%i" % (pos1.x(), pos1.y(), pos2.x(), pos2.y())
        CanvasCallback(ACTION_GROUP_POSITION, group.group_id, 0, valueStr)

    for node in nodes:
        node.repaintLines(True)

    if canvas.scene:
        canvas.scene.zoom_fit()
        canvas.scene.update()
    log_carla("PatchCanvas::autoArrange() finished")


def centerGraphInCanvas():
    if not canvas or not canvas.group_list:
        return
    nodes = []
    for group in canvas.group_list:
        nodes.extend(w for w in group.widgets if w is not None)
    if not nodes:
        return

    min_x = min(n.x() for n in nodes)
    min_y = min(n.y() for n in nodes)
    max_x = max(n.x() + n.boundingRect().width() for n in nodes)
    max_y = max(n.y() + n.boundingRect().height() for n in nodes)

    bbox_w = max_x - min_x
    bbox_h = max_y - min_y

    canvas_w = (
        canvas.size_rect.width()
        if not canvas.size_rect.isNull()
        else (canvas.scene.width() if canvas.scene else 0)
    )
    canvas_h = (
        canvas.size_rect.height()
        if not canvas.size_rect.isNull()
        else (canvas.scene.height() if canvas.scene else 0)
    )
    canvas_x = canvas.size_rect.x() if not canvas.size_rect.isNull() else 0
    canvas_y = canvas.size_rect.y() if not canvas.size_rect.isNull() else 0

    if canvas_w > 0 and canvas_h > 0:
        target_x = canvas_x + (canvas_w - bbox_w) / 2.0
        target_y = canvas_y + (canvas_h - bbox_h) / 2.0
        target_x = max(canvas_x, target_x)
        target_y = max(canvas_y, target_y)
        offset_x = target_x - min_x
        offset_y = target_y - min_y
    else:
        offset_x = 40 - min_x
        offset_y = 40 - min_y

    for node in nodes:
        node.blockSignals(True)
        node.setPos(node.x() + offset_x, node.y() + offset_y)
        node.checkItemPos()
        node.blockSignals(False)

    for group in canvas.group_list:
        pos1 = group.widgets[0].pos()
        pos2 = (
            group.widgets[1].pos()
            if group.split and group.widgets[1]
            else QPointF(0, 0)
        )
        valueStr = "%i:%i:%i:%i" % (pos1.x(), pos1.y(), pos2.x(), pos2.y())
        CanvasCallback(ACTION_GROUP_POSITION, group.group_id, 0, valueStr)

    for node in nodes:
        node.repaintLines(True)

    if canvas.scene:
        canvas.scene.update()




def syncNodePositions(nodes_to_sync):
    if not nodes_to_sync:
        return
    synced_groups = set()
    for node in nodes_to_sync:
        node.blockSignals(True)
        node.checkItemPos()
        node.blockSignals(False)
        node.repaintLines(True)

    for group in canvas.group_list:
        widgets = [w for w in group.widgets if w is not None]
        if any(w in nodes_to_sync for w in widgets):
            synced_groups.add(group)

    for group in synced_groups:
        pos1 = group.widgets[0].pos()
        pos2 = (
            group.widgets[1].pos()
            if group.split and group.widgets[1]
            else QPointF(0, 0)
        )
        if canvas.settings:
            try:
                if group.split:
                    canvas.settings.setValue(
                        "CanvasPositions/%s_OUTPUT" % group.group_name, pos1
                    )
                    if group.widgets[1]:
                        canvas.settings.setValue(
                            "CanvasPositions/%s_INPUT" % group.group_name, pos2
                        )
                else:
                    canvas.settings.setValue(
                        "CanvasPositions/%s" % group.group_name, pos1
                    )
            except Exception:
                pass
        valueStr = "%i:%i:%i:%i" % (pos1.x(), pos1.y(), pos2.x(), pos2.y())
        CanvasCallback(ACTION_GROUP_POSITION, group.group_id, 0, valueStr)

    if canvas.scene:
        canvas.scene.update()


def arrange():
    autoArrange()


def getSelectedNodes():
    selected = []
    if canvas.scene:
        for item in canvas.scene.selectedItems():
            if isinstance(item, CanvasBox):
                selected.append(item)
    return selected


def selectAllNodes():
    if not canvas.scene:
        return
    for group in canvas.group_list:
        for w in group.widgets:
            if w is not None:
                w.setSelected(True)


def deselectAllNodes():
    if canvas.scene:
        canvas.scene.clearSelection()


def invertNodeSelection():
    if not canvas.scene:
        return
    for group in canvas.group_list:
        for w in group.widgets:
            if w is not None:
                w.setSelected(not w.isSelected())


def selectNodesByType(target_type):
    if not canvas.scene:
        return
    for group in canvas.group_list:
        for w in group.widgets:
            if w is not None and hasattr(w, "getNodeBadgeType"):
                if w.getNodeBadgeType() == target_type:
                    w.setSelected(True)


def getAvailableNodeTypes():
    types_found = set()
    for group in canvas.group_list:
        for w in group.widgets:
            if w is not None and hasattr(w, "getNodeBadgeType"):
                types_found.add(w.getNodeBadgeType())
    return sorted(types_found)



def alignSelected(mode="horizontal"):
    """
    mode: 'horizontal' (align Y centers), 'vertical' (align X centers),
          'distribute_h' (spread horizontally), 'distribute_v' (spread vertically)
    """
    nodes = getSelectedNodes()
    if len(nodes) < 2:
        return

    node_gap = 40

    if mode == "horizontal":
        target_y = sum(n.y() for n in nodes) / float(len(nodes))
        nodes.sort(key=lambda n: n.x())
        # First align all Y to target_y
        for n in nodes:
            n.setPos(n.x(), target_y)
        # Push overlapping nodes horizontally to maintain at least node_gap
        for i in range(len(nodes) - 1):
            curr_node = nodes[i]
            next_node = nodes[i + 1]
            min_next_x = curr_node.x() + curr_node.boundingRect().width() + node_gap
            if next_node.x() < min_next_x:
                next_node.setPos(min_next_x, target_y)

    elif mode == "vertical":
        target_x = sum(n.x() for n in nodes) / float(len(nodes))
        nodes.sort(key=lambda n: n.y())
        # First align all X to target_x
        for n in nodes:
            n.setPos(target_x, n.y())
        # Push overlapping nodes vertically to maintain at least node_gap
        for i in range(len(nodes) - 1):
            curr_node = nodes[i]
            next_node = nodes[i + 1]
            min_next_y = curr_node.y() + curr_node.boundingRect().height() + node_gap
            if next_node.y() < min_next_y:
                next_node.setPos(target_x, min_next_y)

    elif mode == "distribute_h":
        nodes.sort(key=lambda n: n.x())
        curr_x = nodes[0].x()
        for n in nodes:
            n.setPos(curr_x, n.y())
            curr_x += n.boundingRect().width() + node_gap

    elif mode == "distribute_v":
        nodes.sort(key=lambda n: n.y())
        curr_y = nodes[0].y()
        for n in nodes:
            n.setPos(n.x(), curr_y)
            curr_y += n.boundingRect().height() + node_gap

    if getattr(options, "snap_enabled", True):
        gs = max(1, getattr(options, "grid_size", 20))
        for n in nodes:
            n.setPos(round(n.x() / gs) * gs, round(n.y() / gs) * gs)

    syncNodePositions(nodes)


def repelNodes(target_nodes=None, iterations=25, padding=24):
    """
    Separates overlapping canvas nodes using iterative AABB repulsion forces.
    If target_nodes is None, defaults to selected nodes (or all nodes if < 2 selected).
    """
    if target_nodes is None:
        target_nodes = getSelectedNodes()
        if len(target_nodes) < 2:
            target_nodes = []
            for group in canvas.group_list:
                for w in group.widgets:
                    if w is not None and w.isVisible():
                        target_nodes.append(w)

    if len(target_nodes) < 2:
        return

    node_list = list(target_nodes)

    for _ in range(iterations):
        moved_any = False
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                n1 = node_list[i]
                n2 = node_list[j]

                r1 = QRectF(n1.x(), n1.y(), n1.boundingRect().width(), n1.boundingRect().height())
                r2 = QRectF(n2.x(), n2.y(), n2.boundingRect().width(), n2.boundingRect().height())

                # Expand r1 bounds by desired padding
                r1_padded = r1.adjusted(-padding / 2, -padding / 2, padding / 2, padding / 2)
                r2_padded = r2.adjusted(-padding / 2, -padding / 2, padding / 2, padding / 2)

                intersect = r1_padded.intersected(r2_padded)
                if not intersect.isEmpty() and intersect.width() > 0 and intersect.height() > 0:
                    moved_any = True
                    # Push along axis of least overlap
                    overlap_x = intersect.width()
                    overlap_y = intersect.height()

                    dx = (r2.center().x() - r1.center().x()) or 1.0
                    dy = (r2.center().y() - r1.center().y()) or 1.0

                    if overlap_x < overlap_y:
                        shift = (overlap_x / 2.0) + 1.0
                        sgn = 1.0 if dx > 0 else -1.0
                        n1.setPos(n1.x() - sgn * shift, n1.y())
                        n2.setPos(n2.x() + sgn * shift, n2.y())
                    else:
                        shift = (overlap_y / 2.0) + 1.0
                        sgn = 1.0 if dy > 0 else -1.0
                        n1.setPos(n1.x(), n1.y() - sgn * shift)
                        n2.setPos(n2.x(), n2.y() + sgn * shift)

        if not moved_any:
            break

    # Snap to grid if active
    if getattr(options, "snap_enabled", True):
        gs = max(1, getattr(options, "grid_size", 20))
        for n in node_list:
            n.setPos(round(n.x() / gs) * gs, round(n.y() / gs) * gs)

    for n in node_list:
        n.checkItemPos()

    syncNodePositions(node_list)


def arrangeConnected(target_box=None, direction="both"):
    """
    Arranges nodes connected to target_box:
      direction: 'before' (upstream sources only),
                 'after' (downstream targets only),
                 'both' (entire connected subgraph)
    """
    port_nodes = {}
    node_to_group = {}
    nodes = []

    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is None or not widget.m_port_list_ids:
                continue
            nodes.append(widget)
            node_to_group[widget] = group
            for port in canvas.port_list:
                if port.widget and port.widget.parentItem() == widget:
                    port_nodes[(port.group_id, port.port_id)] = widget

    if not nodes:
        return

    if target_box is None:
        selected = getSelectedNodes()
        if selected:
            target_box = selected[0]
        else:
            return

    node_set = set(nodes)
    edges = {node: set() for node in nodes}
    incoming = {node: set() for node in nodes}

    for connection in canvas.connection_list:
        source = port_nodes.get((connection.group_out_id, connection.port_out_id))
        target = port_nodes.get((connection.group_in_id, connection.port_in_id))
        if source in node_set and target in node_set and source != target:
            edges[source].add(target)
            incoming[target].add(source)

    # Collect subgraph depending on direction
    subgraph = set()
    subgraph.add(target_box)

    if direction in ("before", "both"):
        queue = [target_box]
        visited_up = {target_box}
        while queue:
            curr = queue.pop(0)
            for p in incoming[curr]:
                if p not in visited_up:
                    visited_up.add(p)
                    subgraph.add(p)
                    queue.append(p)

    if direction in ("after", "both"):
        queue = [target_box]
        visited_down = {target_box}
        while queue:
            curr = queue.pop(0)
            for child in edges[curr]:
                if child not in visited_down:
                    visited_down.add(child)
                    subgraph.add(child)
                    queue.append(child)

    subgraph_nodes = list(subgraph)
    if len(subgraph_nodes) <= 1:
        return

    # Calculate relative horizontal layers anchored around target_box (target_box = 0)
    subgraph_set = set(subgraph_nodes)
    relative_layer = {target_box: 0}

    # Trace upstream (negative relative layer)
    up_queue = [target_box]
    while up_queue:
        curr = up_queue.pop(0)
        curr_lvl = relative_layer[curr]
        for p in incoming[curr]:
            if p in subgraph_set:
                p_lvl = curr_lvl - 1
                if p not in relative_layer or p_lvl < relative_layer[p]:
                    relative_layer[p] = p_lvl
                    up_queue.append(p)

    # Trace downstream (positive relative layer)
    down_queue = [target_box]
    while down_queue:
        curr = down_queue.pop(0)
        curr_lvl = relative_layer[curr]
        for child in edges[curr]:
            if child in subgraph_set:
                child_lvl = curr_lvl + 1
                if child not in relative_layer or child_lvl > relative_layer[child]:
                    relative_layer[child] = child_lvl
                    down_queue.append(child)

    for n in subgraph_nodes:
        if n not in relative_layer:
            relative_layer[n] = 0

    columns = {}
    for n in subgraph_nodes:
        columns.setdefault(relative_layer[n], []).append(n)

    sorted_layers = sorted(columns.keys())

    # Keep target_box at its current position as the anchor
    anchor_x = target_box.x()
    anchor_y = target_box.y()
    node_gap = 64
    vertical_gap = 40

    # Calculate column widths
    col_widths = {
        layer: max(n.boundingRect().width() for n in columns[layer])
        for layer in sorted_layers
    }

    # Determine X coordinates for each column relative to target_box's layer (0)
    col_x = {0: anchor_x}
    # Columns to the right (> 0)
    curr_x = anchor_x + col_widths[0] + node_gap
    for layer in [l for l in sorted_layers if l > 0]:
        col_x[layer] = curr_x
        curr_x += col_widths[layer] + node_gap

    # Columns to the left (< 0)
    curr_x = anchor_x
    for layer in reversed([l for l in sorted_layers if l < 0]):
        curr_x -= col_widths[layer] + node_gap
        col_x[layer] = curr_x

    # Position each column vertically centered around anchor_y
    for layer in sorted_layers:
        col = columns[layer]
        col.sort(key=lambda n: node_to_group[n].group_name)
        total_col_height = (
            sum(n.boundingRect().height() for n in col)
            + (len(col) - 1) * vertical_gap
        )
        if layer == 0 and len(col) == 1 and col[0] == target_box:
            # Keep anchor exactly where it is
            start_y = anchor_y
        else:
            anchor_h = target_box.boundingRect().height()
            start_y = anchor_y + (anchor_h / 2.0) - (total_col_height / 2.0)

        cy = start_y
        for n in col:
            n.setPos(col_x[layer], cy)
            cy += n.boundingRect().height() + vertical_gap

    syncNodePositions(subgraph_nodes)


def autoArrangeAround(box=None, algorithm="flow"):
    """Auto-arrange the subgraph connected to one box, using the active layout algorithm."""
    if box is None:
        selected = getSelectedNodes()
        if not selected:
            return
        box = selected[0]

    port_nodes = {}
    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is None:
                continue
            for port in canvas.port_list:
                if port.widget and port.widget.parentItem() is widget:
                    port_nodes[(port.group_id, port.port_id)] = widget

    adjacency = {}
    for connection in canvas.connection_list:
        source = port_nodes.get((connection.group_out_id, connection.port_out_id))
        target = port_nodes.get((connection.group_in_id, connection.port_in_id))
        if source is None or target is None or source is target:
            continue
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)

    seen = {box}
    queue = [box]
    while queue:
        current = queue.pop(0)
        for neighbour in adjacency.get(current, ()):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)

    nodes = list(seen)
    if len(nodes) < 2:
        return

    autoArrangeNodes(nodes, algorithm)
    syncNodePositions(nodes)


def moveAsideNonConnectedNodes(anchor_node=None):
    """
    Moves all nodes that have zero connections (or are disconnected from the active graph)
    aside into a clean vertical column below/beside the connected subgraph.
    """
    all_nodes = []
    node_to_group = {}
    port_nodes = {}

    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is None or not widget.m_port_list_ids:
                continue
            all_nodes.append(widget)
            node_to_group[widget] = group
            for port in canvas.port_list:
                if port.widget and port.widget.parentItem() == widget:
                    port_nodes[(port.group_id, port.port_id)] = widget

    if len(all_nodes) <= 1:
        return

    # Find connected nodes
    connected_nodes = set()
    for connection in canvas.connection_list:
        p1 = (connection.group_out_id, connection.port_out_id)
        p2 = (connection.group_in_id, connection.port_in_id)
        n1 = port_nodes.get(p1)
        n2 = port_nodes.get(p2)
        if n1 and n2 and n1 != n2:
            connected_nodes.add(n1)
            connected_nodes.add(n2)

    non_connected = [n for n in all_nodes if n not in connected_nodes]
    if not non_connected:
        return

    # Determine bounding area of connected nodes
    if connected_nodes:
        max_x = max(n.x() + n.boundingRect().width() for n in connected_nodes)
        min_y = min(n.y() for n in connected_nodes)
        max_y = max(n.y() + n.boundingRect().height() for n in connected_nodes)
        target_x = max_x + 50
        target_y = min_y
        max_allowed_h = max(400.0, max_y - min_y)
    else:
        target_x = 60
        target_y = 60
        max_allowed_h = 600.0

    non_connected.sort(key=lambda n: node_to_group[n].group_name.lower())
    cx = target_x
    cy = target_y
    vertical_gap = 16
    col_width = 0

    for n in non_connected:
        n_w = n.boundingRect().width()
        n_h = n.boundingRect().height()
        # Wrap into an adjacent column if vertical span exceeds main connected graph height
        if (cy + n_h - target_y) > max_allowed_h and cy > target_y:
            cx += col_width + 24
            cy = target_y
            col_width = n_w
        else:
            col_width = max(col_width, n_w)

        n.setPos(cx, cy)
        cy += n_h + vertical_gap

    syncNodePositions(non_connected)


# ------------------------------------------------------------------------------------------------------------
# Smart arrange / wire / repel API (driven by the canvas "Arrange tools" toolbar)


def _workingNodes(nodes=None):
    """Explicit list -> current selection -> every visible box."""
    if nodes:
        return [n for n in nodes if n is not None]
    selected = getSelectedNodes()
    if selected:
        return list(selected)
    result = []
    for group in canvas.group_list:
        for w in group.widgets:
            if w is not None and w.isVisible():
                result.append(w)
    return result


def _nodeGraph(nodes):
    """Connection edges/incoming restricted to `nodes`, plus a node->group-name map."""
    node_set = set(nodes)
    port_nodes = {}
    group_name = {}
    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is None:
                continue
            if widget in node_set:
                group_name[widget] = group.group_name
            for port in canvas.port_list:
                if port.widget and port.widget.parentItem() == widget:
                    port_nodes[(port.group_id, port.port_id)] = widget

    edges = {n: set() for n in nodes}
    incoming = {n: set() for n in nodes}
    for connection in canvas.connection_list:
        src = port_nodes.get((connection.group_out_id, connection.port_out_id))
        dst = port_nodes.get((connection.group_in_id, connection.port_in_id))
        if src in edges and dst in incoming and src is not dst:
            edges[src].add(dst)
            incoming[dst].add(src)
    return edges, incoming, group_name


def autoArrangeNodes(nodes=None, algorithm=None):
    """Arrange nodes using the selected arrange-algorithm plugin.

    `algorithm` selects a registered LayoutAlgorithm by name; when None the last
    choice from settings (``options.arrange_style``) is used.
    """
    nodes = _workingNodes(nodes)
    resolve_layout_algorithm(algorithm).arrange(nodes)


def autoRepelNodes(nodes=None):
    """Separate overlapping nodes; with nothing selected this repels the whole canvas."""
    nodes = _workingNodes(nodes)
    if len(nodes) >= 2:
        repelNodes(nodes)


def autoWire(nodes=None):
    """Chain the given (or selected / all) nodes in signal-flow order.

    Every consecutive pair is joined by the first compatible, still-free output ->
    input port pair. Connections are requested through the normal canvas callback so
    the engine stays authoritative (proper connection ids / undo). Returns how many
    connections were requested.
    """
    nodes = _workingNodes(nodes)
    if len(nodes) < 2:
        return 0

    edges, incoming, _group_name = _nodeGraph(nodes)

    # Topological order, x position as a stable tie-breaker, cycles broken by x
    ordered = []
    seen = set()
    pending = set(nodes)
    while pending:
        ready = [n for n in pending if not (incoming[n] - seen)]
        if not ready:
            ready = list(pending)
        ready.sort(key=lambda n: n.x())
        chosen = ready[0]
        seen.add(chosen)
        pending.discard(chosen)
        ordered.append(chosen)

    def ports_of(node, mode):
        found = []
        for port in canvas.port_list:
            if port.widget and port.widget.parentItem() == node and port.port_mode == mode:
                found.append(port)
        found.sort(key=lambda p: p.port_id)
        return found

    def is_connected(port):
        for connection in canvas.connection_list:
            if connection.group_out_id == port.group_id and connection.port_out_id == port.port_id:
                return True
            if connection.group_in_id == port.group_id and connection.port_in_id == port.port_id:
                return True
        return False

    count = 0
    for i in range(len(ordered) - 1):
        src = ordered[i]
        dst = ordered[i + 1]
        outs = [p for p in ports_of(src, PORT_MODE_OUTPUT) if not is_connected(p)]
        ins = [p for p in ports_of(dst, PORT_MODE_INPUT) if not is_connected(p)]
        if not outs or not ins:
            continue
        out_port = outs[0]
        in_port = None
        for candidate in ins:
            if candidate.port_type == out_port.port_type:
                in_port = candidate
                break
        if in_port is None:
            in_port = ins[0]
        data = "%i:%i:%i:%i" % (
            out_port.group_id, out_port.port_id,
            in_port.group_id, in_port.port_id,
        )
        canvas.callback(ACTION_PORTS_CONNECT, 0, 0, data)
        count += 1
    return count


def autoArrangeAndWire(nodes=None):
    """Arrange the working set, then wire it in signal-flow order."""
    nodes = _workingNodes(nodes)
    if len(nodes) < 2:
        return 0
    autoArrangeNodes(nodes)
    return autoWire(nodes)


# ------------------------------------------------------------------------------------------------------------


def updateZValues():
    if canvas.debug:
        print("PatchCanvas::updateZValues()")

    for group in canvas.group_list:
        group.widgets[0].resetLinesZValue()

        if group.split and group.widgets[1]:
            group.widgets[1].resetLinesZValue()


# ------------------------------------------------------------------------------------------------------------


def redrawPluginGroup(plugin_id):
    group = canvas.group_plugin_map.get(plugin_id, None)

    if group is None:
        # qCritical("PatchCanvas::redrawPluginGroup(%i) - unable to find group" % plugin_id)
        return

    group.widgets[0].redrawInlineDisplay()

    if group.split and group.widgets[1]:
        group.widgets[1].redrawInlineDisplay()


def handlePluginRemoved(plugin_id):
    if canvas.debug:
        print("PatchCanvas::handlePluginRemoved(%i)" % plugin_id)

    canvas.scene.clearSelection()

    group = canvas.group_plugin_map.pop(plugin_id, None)

    if group is not None:
        group.plugin_id = -1
        group.plugin_ui = False
        group.plugin_inline = False
        group.widgets[0].removeAsPlugin()

        if group.split and group.widgets[1]:
            group.widgets[1].removeAsPlugin()

    for group in canvas.group_list:
        if group.plugin_id < plugin_id or group.plugin_id > MAX_PLUGIN_ID_ALLOWED:
            continue

        group.plugin_id -= 1
        group.widgets[0].m_plugin_id -= 1

        if group.split and group.widgets[1]:
            group.widgets[1].m_plugin_id -= 1

        canvas.group_plugin_map[plugin_id] = group


def handleAllPluginsRemoved():
    if canvas.debug:
        print("PatchCanvas::handleAllPluginsRemoved()")

    canvas.group_plugin_map = {}

    for group in canvas.group_list:
        if group.plugin_id < 0:
            continue
        if group.plugin_id > MAX_PLUGIN_ID_ALLOWED:
            continue

        group.plugin_id = -1
        group.plugin_ui = False
        group.plugin_inline = False
        group.widgets[0].removeAsPlugin()

        if group.split and group.widgets[1]:
            group.widgets[1].removeAsPlugin()


# ------------------------------------------------------------------------------------------------------------
# Layout Containers (VBox, HBox, Grid)


def createContainerFromSelected(layout_mode="vbox", title=None):
    if not canvas.scene:
        return None

    selected_boxes = [item for item in canvas.scene.selectedItems() if item and item.type() == CanvasBoxType]
    if not selected_boxes:
        return None

    from .canvascontainer import CanvasContainer
    c_id = f"container_{len(getattr(canvas, 'container_list', [])) + 1}"
    title = title or f"Group {len(getattr(canvas, 'container_list', [])) + 1}"
    container = CanvasContainer(c_id, title=title, layout_mode=layout_mode)

    if layout_mode == "freeform":
        # Anchor container precisely to the bounding box of selected items so they don't move
        min_x = min(b.x() for b in selected_boxes)
        min_y = min(b.y() for b in selected_boxes)
        container_x = min_x - 14.0
        container_y = min_y - 36.0
        container.setPos(container_x, container_y)

        canvas.scene.addItem(container)
        if not hasattr(canvas, "container_list"):
            canvas.container_list = []
        canvas.container_list.append(container)

        for box in selected_boxes:
            old_c = getattr(box, "_canvas_container", None)
            if old_c:
                old_c.removeItem(box)
            # Store exact relative offset so box stays at current canvas pos
            container.m_item_offsets[box] = (box.x() - container_x, box.y() - container_y)
            container.addItem(box)
    else:
        # Calculate average position of selected boxes for structured layout
        avg_x = sum(b.x() for b in selected_boxes) / len(selected_boxes)
        avg_y = sum(b.y() for b in selected_boxes) / len(selected_boxes)
        container.setPos(avg_x - 14, avg_y - 42)

        canvas.scene.addItem(container)
        if not hasattr(canvas, "container_list"):
            canvas.container_list = []
        canvas.container_list.append(container)

        for box in selected_boxes:
            old_c = getattr(box, "_canvas_container", None)
            if old_c:
                old_c.removeItem(box)
            container.addItem(box)

    container.updateLayout()
    return container


def ungroupNode(box):
    c = getattr(box, "_canvas_container", None)
    if c:
        c.removeItem(box)
        if not c.m_items and not c.m_standby_descriptors:
            if hasattr(canvas, "container_list") and c in canvas.container_list:
                canvas.container_list.remove(c)
            if canvas.scene:
                canvas.scene.removeItem(c)


def saveContainers():
    ret = []
    for c in getattr(canvas, "container_list", []):
        members = [c.getBoxDescriptor(b) for b in c.m_items]
        # Include standby descriptors as well so offline clients stay in group
        for d in c.m_standby_descriptors:
            if d not in members:
                members.append(d)

        ret.append({
            "id": c.m_id,
            "title": c.m_title,
            "type": c.m_layout_mode,
            "color": c.m_color.name() if hasattr(c.m_color, "name") else str(c.m_color),
            "pos": [c.x(), c.y()],
            "members": members,
        })
    return ret


def loadContainers(containers_data):
    if not containers_data or not canvas.scene:
        return

    from qt_compat import QColor
    from .canvascontainer import CanvasContainer

    # Update containers in place: this runs before load, after load and on the
    # deferred sweep, and clearing/recreating made them flicker every time.
    existing = {}
    for c in getattr(canvas, "container_list", []):
        existing[getattr(c, "m_id", None)] = c

    all_boxes = []
    for g in canvas.group_list:
        if g.widgets[0]:
            all_boxes.append(g.widgets[0])
        if g.split and g.widgets[1]:
            all_boxes.append(g.widgets[1])

    seen_ids = set()

    for c_info in containers_data:
        c_id = c_info.get("id", "container")
        seen_ids.add(c_id)
        title = c_info.get("title", "Group")
        ltype = c_info.get("type", "vbox")
        pos = c_info.get("pos", [0, 0])
        members = c_info.get("members", [])

        container = existing.get(c_id)
        created = container is None

        if created:
            container = CanvasContainer(c_id, title=title, layout_mode=ltype)
            canvas.scene.addItem(container)
            canvas.container_list.append(container)
        else:
            container.m_title = title
            container.m_layout_mode = ltype
            container.update()

        container.setPos(pos[0], pos[1])
        if "color" in c_info:
            container.m_color = QColor(c_info["color"])
            container.update()

        for desc in members:
            matched = None
            for box in all_boxes:
                if container.matchesDescriptor(box, desc):
                    matched = box
                    break

            if matched:
                container.addItem(matched)
            elif desc not in container.m_standby_descriptors:
                container.m_standby_descriptors.append(desc)

        container.updateLayout()

        if created:
            print(f"[CONTAINERS] Created '{container.m_title}' pos={container.pos().x()},{container.pos().y()} items={len(container.m_items)} standby={len(container.m_standby_descriptors)}")

    # Drop containers that are no longer in the project
    for c_id, container in existing.items():
        if c_id is None or c_id in seen_ids:
            continue
        if container.scene() == canvas.scene:
            canvas.scene.removeItem(container)
        if container in canvas.container_list:
            canvas.container_list.remove(container)


# ------------------------------------------------------------------------------------------------------------
# Load-time skeleton (ghost groups)

class CanvasGhost(QGraphicsObject):
    """Placeholder drawn from the project file while the real plugin is still loading."""

    def __init__(self, name, left_ports=(), right_ports=()):
        QGraphicsObject.__init__(self)
        from qt_compat import Qt

        self.m_group_name = name
        self.m_left = list(left_ports)
        self.m_right = list(right_ports)
        self.m_bound_group = None
        self.setZValue(-5)
        self.setAcceptedMouseButtons(Qt.NoButton)

        rows = max(len(self.m_left), len(self.m_right), 1)
        self._width = max(150.0, len(name) * 7.5 + 28.0)
        self._height = 26.0 + rows * 10.0 + 8.0

    def bind(self, group):
        """Bind this ghost to its real canvas group. False means the pair does not match."""
        try:
            if group is None or getattr(group, "group_name", None) != self.m_group_name:
                return False
            if not getattr(group, "widgets", None) or group.widgets[0] is None:
                return False
            self.m_bound_group = group
            return True
        except RuntimeError:
            return False

    def boundingRect(self):
        return QRectF(0, 0, self._width, self._height)

    def paint(self, painter, option, widget):
        from qt_compat import QColor, QFont, QPen, QPainter, Qt

        painter.setRenderHint(QPainter.Antialiasing, True)

        bg = QColor(getattr(canvas.theme, "box_bg_1", "#313244"))
        bg.setAlpha(150)
        painter.setBrush(bg)
        painter.setPen(QPen(QColor(137, 180, 250, 130), 1.2, Qt.DashLine))
        painter.drawRoundedRect(QRectF(1, 1, self._width - 2, self._height - 2), 6, 6)

        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(205, 214, 244, 200))
        painter.drawText(QRectF(9, 4, self._width - 18, 16), Qt.AlignLeft | Qt.AlignVCenter, self.m_group_name)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(137, 180, 250, 160))
        y = 24.0
        for i in range(len(self.m_left)):
            painter.drawRoundedRect(QRectF(5, y + i * 10.0, 9, 6), 2, 2)
        for i in range(len(self.m_right)):
            painter.drawRoundedRect(QRectF(self._width - 14, y + i * 10.0, 9, 6), 2, 2)


def addGhostGroup(name, pos, left_ports=(), right_ports=()):
    if not canvas.scene or not name:
        return None
    for ghost in canvas.ghost_list:
        if ghost.m_group_name == name:
            return ghost
    ghost = CanvasGhost(name, left_ports, right_ports)
    ghost.setPos(pos)
    canvas.scene.addItem(ghost)
    canvas.ghost_list.append(ghost)
    return ghost


def removeGhostGroup(name):
    for ghost in list(canvas.ghost_list):
        if ghost.m_group_name == name:
            canvas.ghost_list.remove(ghost)
            if ghost.scene() is canvas.scene:
                canvas.scene.removeItem(ghost)
            return


def clearGhosts():
    for ghost in list(canvas.ghost_list):
        if ghost.scene() is canvas.scene:
            canvas.scene.removeItem(ghost)
    canvas.ghost_list = []


class CanvasGhostCable(QGraphicsObject):
    """Dashed placeholder cable between two ghost groups."""

    def __init__(self, src_name, src_port, dst_name, dst_port):
        QGraphicsObject.__init__(self)
        self.src = (src_name, src_port)
        self.dst = (dst_name, dst_port)
        self._p1 = QPointF(0, 0)
        self._p2 = QPointF(0, 0)
        self._path = None
        self.setZValue(-4)

    def boundingRect(self):
        if self._path is not None:
            return self._path.boundingRect().adjusted(-3, -3, 3, 3)
        from qt_compat import QRectF as _QRectF
        return _QRectF(self._p1, self._p2).normalized().adjusted(-3, -3, 3, 3)

    def _buildPath(self):
        from qt_compat import QPainterPath
        from .linealgos import get_line_algorithm, LineContext, DIRECTION_OUTPUT
        try:
            algorithm = get_line_algorithm(getattr(options, "line_style", "bezier"))
            self._path = algorithm.build_path(LineContext(self._p1, self._p2, DIRECTION_OUTPUT))
        except Exception:
            self._path = QPainterPath(self._p1)
            self._path.lineTo(self._p2)

    def setEndpoints(self, p1, p2):
        self.prepareGeometryChange()
        self._p1 = p1
        self._p2 = p2
        self._buildPath()
        self.update()

    def paint(self, painter, option, widget):
        from qt_compat import QColor, QPen, QPainter, Qt
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen_style = Qt.SolidLine
        if getattr(options, "line_stroke", "solid") == "dotted":
            pen_style = Qt.DotLine
        elif getattr(options, "line_stroke", "solid") == "dashed":
            pen_style = Qt.DashLine
        painter.setPen(QPen(QColor(137, 180, 250, 90), 1.2, pen_style))
        painter.setBrush(Qt.NoBrush)
        if self._path is not None:
            painter.drawPath(self._path)
        else:
            painter.drawLine(self._p1, self._p2)


def _ghostByName(name):
    for ghost in getattr(canvas, "ghost_list", []):
        if ghost.m_group_name == name:
            return ghost
    return None


def _ghostAnchor(ghost, port_name):
    if ghost is None:
        return None
    if port_name in ghost.m_left:
        return ghost.mapToScene(QPointF(9, 27 + ghost.m_left.index(port_name) * 10.0))
    if port_name in ghost.m_right:
        return ghost.mapToScene(QPointF(ghost._width - 9, 27 + ghost.m_right.index(port_name) * 10.0))
    return None


def addGhostCable(src_name, src_port, dst_name, dst_port):
    if not canvas.scene:
        return None
    src = _ghostByName(src_name)
    dst = _ghostByName(dst_name)
    p1 = _ghostAnchor(src, src_port) if src is not None else None
    p2 = _ghostAnchor(dst, dst_port) if dst is not None else None
    if p1 is None:
        p1 = _anchorFor(src_name, src_port)
    if p2 is None:
        p2 = _anchorFor(dst_name, dst_port)
    if p1 is None or p2 is None:
        return None
    cable = CanvasGhostCable(src_name, src_port, dst_name, dst_port)
    cable.setEndpoints(p1, p2)
    canvas.scene.addItem(cable)
    canvas.ghost_cable_list.append(cable)
    return cable


def removeGhostCable(src_name, src_port, dst_name, dst_port):
    for cable in list(canvas.ghost_cable_list):
        if cable.src == (src_name, src_port) and cable.dst == (dst_name, dst_port):
            canvas.ghost_cable_list.remove(cable)
            if cable.scene() is canvas.scene:
                canvas.scene.removeItem(cable)
            return


def snapGhostCables(group_name, port_name, pos):
    for cable in list(canvas.ghost_cable_list):
        try:
            if cable.src == (group_name, port_name):
                cable.setEndpoints(pos, cable._p2)
            elif cable.dst == (group_name, port_name):
                cable.setEndpoints(cable._p1, pos)
        except RuntimeError:
            pass


def clearGhostCables():
    for cable in list(getattr(canvas, "ghost_cable_list", [])):
        if cable.scene() is canvas.scene:
            canvas.scene.removeItem(cable)
    canvas.ghost_cable_list = []


# ------------------------------------------------------------------------------------------------------------
# Bindable load shells

def addGroupShell(name, pos, split, left_ports, right_ports, hide_unconnected=False, color="", port_modes=None, is_plugin=False, port_types=None, size=None):
    """Create a real canvas node from the project file, with placeholder port ids.
    The engine callbacks bind these ids later; nothing is recreated."""
    if not canvas.scene or not name:
        return None

    existing = _groupByName(name)
    if existing is not None and not getattr(existing.widgets[0], "_shell", False):
        # Client already exists (engine running): reuse it instead of creating a duplicate.
        for widget in existing.widgets:
            if widget is None:
                continue
            widget.setPos(pos)
            if color:
                widget.setCustomColor(color, notify=False)
            if hide_unconnected:
                widget.setHideUnconnectedPorts(True)
        return existing

    gid = getattr(canvas, "next_shell_group_id", -100000)
    canvas.next_shell_group_id = gid - 1

    icon = ICON_APPLICATION
    group_box = CanvasBox(gid, name, icon)
    group_box.blockSignals(True)
    group_box.setPos(pos)
    group_sbox = None
    if split:
        group_box.setSplit(True, PORT_MODE_OUTPUT)
        group_sbox = CanvasBox(gid, name, icon)
        group_sbox.blockSignals(True)
        group_sbox.setSplit(True, PORT_MODE_INPUT)
        group_sbox.setPos(pos.x() + group_box.boundingRect().width() + 300, pos.y())

    for widget in (group_box, group_sbox):
        if widget is not None:
            widget._shell = True
            widget._shell_name = name
            widget._shell_bound = False
            # same hide state as the final node, so the shell is born at the final size
            widget.m_hide_unconnected_ports = bool(hide_unconnected)
            widget._shell_saved_hide = bool(hide_unconnected)
            widget._shell_reserve_subbar = bool(is_plugin)
            if color:
                widget.setCustomColor(color, notify=False)

    group_dict = group_dict_t()
    group_dict.group_id = gid
    group_dict.group_name = name
    group_dict.pw_node_name = name
    group_dict.split = bool(split)
    group_dict.icon = icon
    group_dict.plugin_id = -1
    group_dict.plugin_ui = False
    group_dict.plugin_inline = False
    group_dict.widgets = [group_box, group_sbox]

    port_types = port_types or {}

    def _add_shell_port(target, port_id, mode, port_name):
        ptype = port_types.get(port_name, PORT_TYPE_AUDIO_JACK)
        widget = target.addPortFromGroup(port_id, mode, ptype, port_name, False, backend_group_id=gid)
        port_dict = getattr(widget, "_port_dict", None)
        if port_dict is not None:
            port_dict.group_id = gid
            port_dict.port_id = port_id
            port_dict.port_name = port_name
            port_dict.port_mode = mode
            port_dict.port_type = ptype
            port_dict.is_alternate = False
            port_dict.widget = widget
            canvas.port_list.append(port_dict)

    port_modes = port_modes or {}
    port_id = -1
    for port_name in list(left_ports) + list(right_ports):
        mode = port_modes.get(port_name)
        if mode is None:
            mode = PORT_MODE_INPUT if port_name in right_ports else PORT_MODE_OUTPUT
        target = group_sbox if (group_sbox is not None and mode == PORT_MODE_INPUT) else group_box
        _add_shell_port(target, port_id, mode, port_name)
        port_id -= 1

    group_box.blockSignals(False)
    if group_sbox is not None:
        group_sbox.blockSignals(False)
    # size to all saved ports, not just the header
    if size and not split:
        group_box._shell_saved_size = (float(size[0]), float(size[1]))
    group_box.relayout()
    if group_sbox is not None:
        group_sbox.relayout()
    group_box._shell_initial_size = (group_box.p_width, group_box.p_height)
    if group_sbox is not None:
        group_sbox._shell_initial_size = (group_sbox.p_width, group_sbox.p_height)
    group_box.checkItemPos()
    if group_sbox is not None:
        group_sbox.checkItemPos()

    canvas.last_z_value += 1
    group_box.setZValue(canvas.last_z_value)
    if group_sbox is not None:
        canvas.last_z_value += 1
        group_sbox.setZValue(canvas.last_z_value)

    canvas.group_list.append(group_dict)
    log_carla(f"patchcanvas.addGroupShell: created '{name}' placeholder id={gid} ports={len(left_ports)}+{len(right_ports)} size={group_box.p_width}x{group_box.p_height}", level="debug")

    if hasattr(canvas, "container_list"):
        for container in canvas.container_list:
            for desc in list(container.m_standby_descriptors):
                if container.matchesDescriptor(group_box, desc):
                    container.addItem(group_box)
                    break
            if group_sbox is not None:
                for desc in list(container.m_standby_descriptors):
                    if container.matchesDescriptor(group_sbox, desc):
                        container.addItem(group_sbox)
                        break

    return group_dict


def bindGroupShell(name, client_id, plugin_id=-1):
    """Bind a shell to the engine ids. Returns the bound group, or None when no shell matches."""
    for group in canvas.group_list:
        box = group.widgets[0]
        if box is None or not getattr(box, "_shell", False):
            continue
        if getattr(box, "_shell_name", None) != name or getattr(box, "_shell_bound", False):
            continue
        old_group_id = group.group_id
        group.group_id = client_id
        group.plugin_id = plugin_id
        for conn in canvas.connection_list:
            if conn.group_out_id == old_group_id:
                conn.group_out_id = client_id
            if conn.group_in_id == old_group_id:
                conn.group_in_id = client_id
        for widget in group.widgets:
            if widget is None:
                continue
            try:
                widget.m_group_id = client_id
                widget.m_plugin_id = plugin_id
                widget._shell_reserve_subbar = False
                widget._shell_bound = True
                widget.relayout()
                widget.update()
            except RuntimeError:
                pass
        for port in canvas.port_list:
            if port.widget is None:
                continue
            try:
                if port.widget.parentItem() not in group.widgets:
                    continue
                port.group_id = client_id
                port_dict = getattr(port.widget, "_port_dict", None)
                if port_dict is not None:
                    port_dict.group_id = client_id
                if hasattr(port.widget, "m_group_id"):
                    port.widget.m_group_id = client_id
            except RuntimeError:
                pass
        # Ports can arrive before their client (engine already running): replay them now.
        pending_ports = canvas.pending_ports.pop(client_id, None)
        if pending_ports:
            for port_id, port_name, port_mode, port_type, is_alternate in pending_ports:
                addPort(client_id, port_id, port_name, port_mode, port_type, is_alternate)
        log_carla(f"patchcanvas.bindGroupShell: bound '{name}' to client {client_id} plugin {plugin_id}", level="debug")
        return group
    return None


def finalizeShells():
    """Drop shells whose plugin never loaded and placeholder ports that never bound."""
    for group in list(canvas.group_list):
        box = group.widgets[0]
        if box is None or not getattr(box, "_shell", False):
            continue
        if not getattr(box, "_shell_bound", False):
            log_carla(f"patchcanvas.finalizeShells: dropping unbound shell '{group.group_name}'", level="debug")
            removeGroup(group.group_id)
            continue
        for port in list(canvas.port_list):
            if port.group_id == group.group_id and getattr(port, "port_id", 0) < 0:
                removePort(group.group_id, port.port_id)
        for widget in group.widgets:
            initial = getattr(widget, "_shell_initial_size", None) if widget is not None else None
            if widget is not None and initial is not None:
                # heal any stale geometry left by the engine's port-insertion order
                widget.relayout()
            if initial is not None:
                try:
                    if abs(widget.p_width - initial[0]) > 0.5 or abs(widget.p_height - initial[1]) > 0.5:
                        log_carla(
                            f"SHELLDIFF '{group.group_name}' shell={initial[0]:.0f}x{initial[1]:.0f} final={widget.p_width:.0f}x{widget.p_height:.0f}",
                            level="warn",
                        )
                except RuntimeError:
                    pass
        # confirmed: apply the saved "hide unused ports" setting once
        for widget in group.widgets:
            if widget is not None and getattr(widget, "_shell_saved_hide", False):
                widget.setHideUnconnectedPorts(True)

    # Any placeholder port the engine never replaced is a ghost: it cannot be connected
    # and its negative id trips an engine assertion. Remove the item, not just the dict.
    for port in list(canvas.port_list):
        if getattr(port, "port_id", 0) >= 0:
            continue
        widget = getattr(port, "widget", None)
        parent = None
        try:
            parent = widget.parentItem() if widget is not None else None
        except RuntimeError:
            parent = None
        if widget is not None:
            try:
                canvas.scene.removeItem(widget)
            except (RuntimeError, TypeError):
                pass
        if parent is not None and port.port_id in getattr(parent, "m_port_list_ids", []):
            parent.removePortFromGroup(port.port_id)
        try:
            canvas.port_list.remove(port)
        except ValueError:
            pass

    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is None:
                continue
            for child in list(widget.childItems()):
                pd = getattr(child, "_port_dict", None)
                if pd is not None and getattr(pd, "port_id", 0) < 0:
                    try:
                        canvas.scene.removeItem(child)
                    except RuntimeError:
                        pass

    ghosts = [p.port_id for p in canvas.port_list if getattr(p, "port_id", 0) < 0]
    if ghosts:
        log_carla(f"finalizeShells: unbound placeholder ports remain: {ghosts}", level="warn")


def addShellConnection(src_name, src_port_name, dst_name, dst_port_name):
    """Create a real cable between shell ports with a temporary negative connection id."""
    src_group = _groupByName(src_name)
    dst_group = _groupByName(dst_name)
    if src_group is None or dst_group is None:
        return None
    if src_group.group_id >= 0 and dst_group.group_id >= 0:
        # both nodes already exist as real clients: the engine owns this cable
        return None
    src_port = next((p for p in canvas.port_list if p.group_id == src_group.group_id and p.port_name == src_port_name), None)
    dst_port = next((p for p in canvas.port_list if p.group_id == dst_group.group_id and p.port_name == dst_port_name), None)
    if src_port is None or dst_port is None or src_port.widget is None or dst_port.widget is None:
        return None
    temp_id = getattr(canvas, "next_shell_connection_id", -1)
    canvas.next_shell_connection_id = temp_id - 1
    connectPorts(temp_id, src_group.group_id, src_port.port_id, dst_group.group_id, dst_port.port_id, fromSplitOrJoin=True)
    log_carla(f"patchcanvas.addShellConnection: temp id={temp_id} {src_name}:{src_port_name} -> {dst_name}:{dst_port_name}", level="debug")
    return temp_id


def bindShellConnection(connection_id, group_out_id, port_out_id, group_in_id, port_in_id):
    for conn in canvas.connection_list:
        if conn.connection_id >= 0:
            continue
        if (conn.group_out_id, conn.port_out_id, conn.group_in_id, conn.port_in_id) != (group_out_id, port_out_id, group_in_id, port_in_id):
            continue
        old_id = conn.connection_id
        conn.connection_id = connection_id
        for group in canvas.group_list:
            for widget in group.widgets:
                if widget is None:
                    continue
                for cb in getattr(widget, "m_connection_lines", []):
                    if cb.connection_id == old_id:
                        cb.connection_id = connection_id
        log_carla(f"patchcanvas.bindShellConnection: {old_id} -> {connection_id}", level="debug")
        return True
    return False


def auditGroupAABBs():
    """Compare each group's box AABB with the AABB of everything drawn inside it."""
    mismatched = 0

    def _grow(rect, item):
        if not item.isVisible():
            return rect
        r = item.sceneBoundingRect()
        return r if rect.isNull() else rect.united(r)

    for group in canvas.group_list:
        widgets = [w for w in group.widgets if w is not None]
        if not widgets:
            continue
        try:
            box_rect = QRectF()
            content_rect = QRectF()
            for widget in widgets:
                box_rect = _grow(box_rect, widget)
                for child in widget.childItems():
                    content_rect = _grow(content_rect, child)
                    for sub in child.childItems():
                        content_rect = _grow(content_rect, sub)
            if box_rect.isNull():
                continue
            content_rect = box_rect if content_rect.isNull() else content_rect.united(box_rect)
            dw = content_rect.width() - box_rect.width()
            dh = content_rect.height() - box_rect.height()
            if abs(dw) > 1.0 or abs(dh) > 1.0:
                mismatched += 1
                log_carla(
                    f"GROUPAABB '{group.group_name}' box={box_rect.width():.0f}x{box_rect.height():.0f} "
                    f"content={content_rect.width():.0f}x{content_rect.height():.0f} "
                    f"dw={dw:+.0f} dh={dh:+.0f}",
                    level="warn",
                )
        except RuntimeError:
            continue

    log_carla(f"GROUPAABB: {mismatched} group(s) whose content extends past the box", level="info")


def auditContainerAABBs():
    """Compare each container's frame with the AABB of its complete member content."""
    mismatched = 0

    def _grow(rect, item):
        if not item.isVisible():
            return rect
        r = item.sceneBoundingRect()
        return r if rect.isNull() else rect.united(r)

    for container in getattr(canvas, "container_list", []):
        try:
            frame = container.sceneBoundingRect()
            box_rect = QRectF()
            content_rect = QRectF()
            members = [b for b in container.m_items if b is not None]
            for box in members:
                box_rect = _grow(box_rect, box)
                content_rect = _grow(content_rect, box)
                for child in box.childItems():
                    content_rect = _grow(content_rect, child)
                    for sub in child.childItems():
                        content_rect = _grow(content_rect, sub)
            if content_rect.isNull():
                content_rect = box_rect
            dw = content_rect.width() - frame.width()
            dh = content_rect.height() - frame.height()
            outside = (
                content_rect.left() < frame.left() - 1
                or content_rect.top() < frame.top() - 1
                or content_rect.right() > frame.right() + 1
                or content_rect.bottom() > frame.bottom() + 1
            )
            if outside:
                mismatched += 1
            log_carla(
                f"CONTAINERAABB '{container.m_title}' frame={frame.width():.0f}x{frame.height():.0f} "
                f"boxes={box_rect.width():.0f}x{box_rect.height():.0f} "
                f"content={content_rect.width():.0f}x{content_rect.height():.0f} "
                f"dw={dw:+.0f} dh={dh:+.0f} members={len(members)} outside={outside}",
                level="warn" if outside else "info",
            )
        except RuntimeError:
            continue

    log_carla(f"CONTAINERAABB: {mismatched} container(s) whose content extends past the frame", level="info")


def snapshotShellSizes():
    """Record shell geometry once cables are wired, so finalizeShells compares like with like."""
    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is not None and getattr(widget, "_shell", False):
                widget._shell_initial_size = (widget.p_width, widget.p_height)


def finalizeShellConnections():
    for conn in list(canvas.connection_list):
        if conn.connection_id < 0:
            log_carla(f"patchcanvas.finalizeShellConnections: dropping unbound cable {conn.connection_id}", level="debug")
            disconnectPorts(conn.connection_id)


def _groupByName(name):
    for group in canvas.group_list:
        if group.group_name == name:
            return group
    return None


def _anchorFor(name, port_name):
    group = _groupByName(name)
    if group is None:
        return None
    for port in canvas.port_list:
        if port.group_id == group.group_id and port.port_name == port_name and port.widget is not None:
            try:
                return port.widget.sceneBoundingRect().center()
            except RuntimeError:
                return None
    return None
