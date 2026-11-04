#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

"""Checks for the pw-record sampler: target naming, node-id resolution and the
"never hand a name to pw-record" guard.

Run with: python3 source/tests/test_pwrecord.py
"""

import importlib.util
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(HERE, "..", "frontend", "patchcanvas", "pwrecord.py")


def load_module():
    spec = importlib.util.spec_from_file_location("pwrecord_under_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PW_DUMP = [
    {"type": "PipeWire:Interface:Node", "id": 44,
     "info": {"props": {"node.name": "BUS-SOUNDBOARD"}}},
    {"type": "PipeWire:Interface:Node", "id": 501,
     "info": {"props": {"node.name": "spotify", "application.name": "Spotify"}}},
    {"type": "PipeWire:Interface:Node", "id": 64,
     "info": {"props": {"node.name": "linuxsoundboard.local_playback"}}},
]


class FakeProc(object):
    def __init__(self):
        self.stdout = types.SimpleNamespace(fileno=lambda: 0)

    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        pass

    def kill(self):
        pass


def test_target_name(module):
    sampler = module.PwRecordSampler()
    assert sampler._target_name("Spotify/spotify") == "spotify"
    assert sampler._target_name("Zen") == "Zen"
    assert sampler._target_name("Client/Node") == "Node"


def test_resolve_ids(module):
    sampler = module.PwRecordSampler()

    def fake_run(args, **kwargs):
        assert args[0] == "pw-dump"
        return types.SimpleNamespace(stdout=json.dumps(PW_DUMP))

    original_run = module.subprocess.run
    module.subprocess.run = fake_run
    try:
        assert sampler._resolve_target("BUS-SOUNDBOARD") == 44
        assert sampler._resolve_target("Spotify/spotify") == 501
        assert sampler._resolve_target("linuxsoundboard.local_playback") == 64
        # unknown names must stay names, so _spawn can refuse them
        assert sampler._resolve_target("OUT-Laptop") == "OUT-Laptop"
    finally:
        module.subprocess.run = original_run


def test_never_spawn_with_a_name(module):
    sampler = module.PwRecordSampler()
    spawned = []

    def fake_run(args, **kwargs):
        return types.SimpleNamespace(stdout=json.dumps(PW_DUMP))

    def fake_popen(args, **kwargs):
        spawned.append(args)
        return FakeProc()

    original_run = module.subprocess.run
    original_popen = module.subprocess.Popen
    original_blocking = module.os.set_blocking
    module.subprocess.run = fake_run
    module.subprocess.Popen = fake_popen
    module.os.set_blocking = lambda fd, flag: None
    try:
        sampler.set_nodes(["OUT-Laptop", "Linux_Soundboard_Output"])
        assert spawned == [], "unresolved names must not start a capture stream"

        sampler.set_nodes(["BUS-SOUNDBOARD", "Spotify/spotify"])
        targets = [args[args.index("--target") + 1] for args in spawned]
        assert sorted(targets) == ["44", "501"], targets
    finally:
        module.subprocess.run = original_run
        module.subprocess.Popen = original_popen
        module.os.set_blocking = original_blocking
        sampler.stop()


def test_ignores_own_capture_clients(module):
    sampler = module.PwRecordSampler()
    sampler.set_nodes(["pw-record-123", "pw-record"])
    assert sampler._procs == {}, "must never sample our own capture clients"


def main():
    module = load_module()
    test_target_name(module)
    test_resolve_ids(module)
    test_never_spawn_with_a_name(module)
    test_ignores_own_capture_clients(module)
    print("pwrecord: all checks passed")


if __name__ == "__main__":
    main()
