#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Skeleton shells must bind even when JACK suffixes a client name (-01, -02).

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from patchcanvas import patchcanvas


class FakeBox:
    def __init__(self, name):
        self._shell = True
        self._shell_name = name
        self._shell_bound = False
        self._shell_reserve_subbar = True
        self.m_group_id = 0
        self.m_plugin_id = -1
        self.relayout_calls = 0

    def relayout(self):
        self.relayout_calls += 1

    def update(self):
        pass

    def childItems(self):
        return []


class FakeGroup:
    def __init__(self, gid, name):
        self.group_id = gid
        self.group_name = name
        self.plugin_id = -1
        self.widgets = [FakeBox(name)]


class FakeScene:
    def items(self):
        return []

    def removeItem(self, item):
        pass


class FakeCanvas:
    def __init__(self, groups):
        self.group_list = groups
        self.port_list = []
        self.connection_list = []
        self.pending_ports = {}
        self.scene = FakeScene()


def bind(name, gid=42, plugin=7):
    saved = patchcanvas.canvas
    fake = FakeCanvas([FakeGroup(1, "MIX-OUTPUT-IEM")])
    patchcanvas.canvas = fake
    try:
        group = patchcanvas.bindGroupShell(name, gid, plugin)
        return group, fake
    finally:
        patchcanvas.canvas = saved


def test_exact_name_binds():
    group, _fake = bind("MIX-OUTPUT-IEM")
    assert group is not None and group.group_id == 42 and group.plugin_id == 7


def test_jack_suffix_still_binds():
    group, _fake = bind("MIX-OUTPUT-IEM-01")
    assert group is not None and group.group_id == 42
    assert group.widgets[0]._shell_bound is True


def test_unknown_name_does_not_bind():
    group, _fake = bind("SOMETHING-ELSE-01")
    assert group is None


def test_canonical_name():
    assert patchcanvas.canonical_client_name("MIX-OUTPUT-IEM-01") == "MIX-OUTPUT-IEM"
    assert patchcanvas.canonical_client_name("MIX-OUTPUT-IEM-12") == "MIX-OUTPUT-IEM"
    assert patchcanvas.canonical_client_name("MIX-OUTPUT-IEM") == "MIX-OUTPUT-IEM"
    assert patchcanvas.canonical_client_name("Bus 1-2") == "Bus 1-2"




def test_finalize_keeps_bound_and_drops_unbound():
    bound = FakeGroup(1, "bound")
    bound.widgets[0]._shell_bound = True
    unbound = FakeGroup(2, "unbound")
    saved = patchcanvas.canvas
    saved_remove = patchcanvas.removeGroup
    fake = FakeCanvas([bound, unbound])
    patchcanvas.canvas = fake

    def fake_remove(gid):
        fake.group_list[:] = [g for g in fake.group_list if g.group_id != gid]

    patchcanvas.removeGroup = fake_remove
    try:
        patchcanvas.finalizeShells()
        assert [g.group_name for g in fake.group_list] == ["bound"]
    finally:
        patchcanvas.canvas = saved
        patchcanvas.removeGroup = saved_remove

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("shell_binding: all checks passed")
