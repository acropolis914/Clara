#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Replace/adopt/rewire host flow, using fake canvas groups (no engine needed).

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from qt_compat import QApplication, QPointF

import rewire_flow
from rewire_flow import RewireFlowMixin

app = QApplication.instance() or QApplication([])


class FakeColor:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class FakeWidget:
    def __init__(self):
        self._pos = QPointF(0, 0)
        self.m_custom_color = None
        self.m_hide_unconnected_ports = False
        self.selected = False

    def pos(self):
        return self._pos

    def setPos(self, pos):
        self._pos = QPointF(pos)

    def setCustomColor(self, color, notify=True):
        self.m_custom_color = FakeColor(color)

    def setHideUnconnectedPorts(self, flag):
        self.m_hide_unconnected_ports = bool(flag)

    def setSelected(self, flag):
        self.selected = bool(flag)


class FakeGroup:
    def __init__(self, gid, name, plugin_id=-1, split=False):
        self.group_id = gid
        self.group_name = name
        self.plugin_id = plugin_id
        self.split = split
        self.widgets = [FakeWidget()]
        if split:
            self.widgets.append(FakeWidget())


class FakeContainer:
    def __init__(self):
        self.items = []

    def containsBox(self, box):
        return box in self.items

    def removeItem(self, box, to_standby=False):
        if box in self.items:
            self.items.remove(box)

    def addItem(self, box):
        self.items.append(box)


class FakeScene:
    def clearSelection(self):
        pass


class FakeCanvas:
    def __init__(self):
        self.group_list = []
        self.port_list = []
        self.connection_list = []
        self.container_list = []
        self.group_plugin_map = {}
        self.scene = FakeScene()


class FakeStatusBar:
    def showMessage(self, *_args):
        pass


class FakeHost(RewireFlowMixin):
    def __init__(self, canvas):
        self.canvas = canvas
        self.fExternalPatchbay = True
        self.fPluginList = []
        self.ui = type("UI", (), {})()
        self.ui.statusbar = FakeStatusBar()
        self.marked = 0
        self.connects = []
        self.host = self

    def markProjectModified(self):
        self.marked += 1

    def updateMiniCanvasLater(self):
        pass

    def get_plugin_info(self, plugin_id):
        return {"label": "Limiter Stereo"}

    def patchbay_connect(self, external, out_gid, out_port, in_gid, in_port):
        self.connects.append((out_gid, out_port, in_gid, in_port))
        return True


_canvas = FakeCanvas()
_patchcanvas = rewire_flow.patchcanvas
_patchcanvas.canvas = _canvas


def _remove_group(gid):
    _canvas.group_list[:] = [g for g in _canvas.group_list if g.group_id != gid]
    _canvas.group_plugin_map = {
        pid: g for pid, g in _canvas.group_plugin_map.items() if g.group_id != gid
    }


def _split_group(gid):
    for group in _canvas.group_list:
        if group.group_id == gid and not group.split:
            group.split = True
            group.widgets.append(FakeWidget())


_patchcanvas.removeGroup = _remove_group
_patchcanvas.splitGroup = _split_group


def reset():
    _canvas.group_list.clear()
    _canvas.port_list.clear()
    _canvas.connection_list.clear()
    _canvas.container_list.clear()
    _canvas.group_plugin_map.clear()


def test_adopt_keeps_place_container_and_color():
    reset()
    old = FakeGroup(1, "MIX-OUTPUT-IEM", plugin_id=5, split=True)
    old.widgets[0].setPos(QPointF(100, 200))
    old.widgets[1].setPos(QPointF(400, 200))
    old.widgets[0].setCustomColor("#123456")
    old.widgets[0].m_hide_unconnected_ports = True
    new = FakeGroup(9, "MIX-OUTPUT-IEM-01", plugin_id=5)
    container = FakeContainer()
    container.addItem(old.widgets[0])
    container.addItem(old.widgets[1])
    _canvas.group_list = [old, new]
    _canvas.container_list = [container]
    _canvas.group_plugin_map = {5: new}

    FakeHost(_canvas)._adoptRewiredNode(1, new)

    assert old.group_id not in [g.group_id for g in _canvas.group_list]
    assert new.widgets[0].pos() == QPointF(100, 200)
    assert new.split and new.widgets[1].pos() == QPointF(400, 200)
    assert new.widgets[0].m_custom_color.name() == "#123456"
    assert new.widgets[0].m_hide_unconnected_ports is True
    assert new.widgets[0] in container.items and old.widgets[0] not in container.items
    assert _canvas.group_plugin_map[5] is new


def test_poll_adopts_as_soon_as_the_new_client_appears():
    reset()
    old = FakeGroup(1, "VU Meter", plugin_id=3)
    old.widgets[0].setPos(QPointF(50, 60))
    new = FakeGroup(9, "VU Meter-01", plugin_id=3)
    _canvas.group_list = [old, new]
    _canvas.group_plugin_map = {3: new}
    host = FakeHost(_canvas)
    host._rewireState = {
        "pluginId": 3, "old_gid": 1, "old_name": "VU Meter",
        "plan": [], "connections": [], "label": "VU Meter",
        "deadline": time.monotonic() + 5.0, "started": time.monotonic(),
        "last_count": -1, "adopted": False,
    }

    host._pollRewire()

    assert host._rewireState["adopted"] is True
    assert old.group_id not in [g.group_id for g in _canvas.group_list]
    assert new.widgets[0].pos() == old.widgets[0].pos()


def test_finish_rewires_cables_and_sweeps_the_ghost():
    reset()
    old = FakeGroup(1, "VU Meter", plugin_id=3)
    new = FakeGroup(9, "VU Meter-01", plugin_id=3)
    ghost = FakeGroup(11, "VU Meter", plugin_id=-1)
    kept_group = FakeGroup(12, "VU Meter", plugin_id=-1)
    kept_group_port = type("Port", (), {"group_id": 12, "port_id": 1, "widget": object()})()
    _canvas.group_list = [old, new, ghost, kept_group]
    _canvas.port_list = [kept_group_port]
    _canvas.group_plugin_map = {3: new}
    host = FakeHost(_canvas)
    host._rewireState = {
        "pluginId": 3, "old_gid": 1, "old_name": "VU Meter",
        "plan": [{
            "old": {"key": 10},
            "target": {"mode": "out", "kind": "audio", "name": "Output L"},
            "reason": "name",
        }],
        "connections": [(1, 10, 7, 3)],
        "label": "Limiter Stereo",
        "deadline": time.monotonic() + 5.0, "started": time.monotonic(),
        "last_count": -1, "adopted": True,
    }
    new_ports = [{"key": 20, "name": "Output L", "mode": "out", "kind": "audio", "index": 0}]

    host._finishRewire(new, new_ports)

    assert host.connects == [(9, 20, 7, 3)]
    assert host._rewireResult["kept"] == 1 and host._rewireResult["failed"] == 0
    assert host.marked == 1
    assert new.widgets[0].selected is True
    assert ghost.group_id not in [g.group_id for g in _canvas.group_list]
    assert kept_group.group_id in [g.group_id for g in _canvas.group_list], "a group with ports must stay"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("rewire_flow: all checks passed")
