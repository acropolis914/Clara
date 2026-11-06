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
from canvas_logic import autoConnectStereoPair, findStereoPartnerConnection
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
            f"connect {gOut}:{pOut} -> {gIn}:{pIn} (external={gCarla.gui.fExternalPatchbay})",
            level="debug",
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
