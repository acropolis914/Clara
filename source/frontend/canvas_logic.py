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
