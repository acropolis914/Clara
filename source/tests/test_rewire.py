#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Pure tests for the replace-in-place port matcher.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from rewire import (
    KIND_AUDIO,
    KIND_MIDI,
    MODE_IN,
    MODE_OUT,
    actual_target,
    match_ports,
    normalize_port,
    resolve_target,
    role_target,
    validate_rows,
)


def port(name, mode, kind, port_id):
    return {"key": port_id, "name": name, "mode": mode, "kind": kind, "index": 0}


def test_exact_name_wins():
    old = [port("Left In", MODE_IN, KIND_AUDIO, 1), port("Right In", MODE_IN, KIND_AUDIO, 2)]
    new = [port("Right In", MODE_IN, KIND_AUDIO, 11), port("Left In", MODE_IN, KIND_AUDIO, 12)]
    rows = match_ports(old, new)
    by_old = {row["old"]["key"]: row for row in rows}
    assert by_old[1]["target"]["name"] == "Left In"
    assert by_old[2]["target"]["name"] == "Right In"
    assert all(row["reason"] == "name" for row in rows)


def test_channel_fallback_and_event():
    old = [port("out_L", MODE_OUT, KIND_AUDIO, 1), port("out_R", MODE_OUT, KIND_AUDIO, 2),
           port("event-in", MODE_IN, KIND_MIDI, 3)]
    new = [port("Output 1", MODE_OUT, KIND_AUDIO, 10), port("Output 2", MODE_OUT, KIND_AUDIO, 11),
           port("events-in", MODE_IN, KIND_MIDI, 12)]
    rows = match_ports(old, new)
    by_old = {row["old"]["key"]: row for row in rows}
    assert by_old[1]["target"]["name"] == "Output 1"
    assert by_old[2]["target"]["name"] == "Output 2"
    assert by_old[3]["target"]["name"] == "events-in"
    assert by_old[1]["reason"] == "channel"
    assert by_old[3]["reason"] == "channel"


def test_direction_and_kind_never_mix():
    old = [port("out", MODE_OUT, KIND_AUDIO, 1)]
    new = [port("in", MODE_IN, KIND_AUDIO, 10), port("midi", MODE_OUT, KIND_MIDI, 11)]
    rows = match_ports(old, new)
    assert rows[0]["target"] is None and rows[0]["reason"] == "none"


def test_role_mode_and_resolution():
    old = [port("a", MODE_OUT, KIND_AUDIO, 1), port("b", MODE_OUT, KIND_AUDIO, 2),
           port("e", MODE_IN, KIND_MIDI, 3)]
    rows = match_ports(old, None)
    assert all(row["target"] and "role" in row["target"] for row in rows)
    new = [port("Left", MODE_OUT, KIND_AUDIO, 10), port("Right", MODE_OUT, KIND_AUDIO, 11),
           port("events-in", MODE_IN, KIND_MIDI, 12)]
    resolved = {row["old"]["key"]: resolve_target(row["target"], new) for row in rows}
    assert resolved[1]["name"] == "Left"
    assert resolved[2]["name"] == "Right"
    assert resolved[3]["name"] == "events-in"


def test_duplicate_output_target_is_rejected():
    old = [port("a", MODE_OUT, KIND_AUDIO, 1), port("b", MODE_OUT, KIND_AUDIO, 2)]
    target = actual_target(port("Out", MODE_OUT, KIND_AUDIO, 10))
    rows = [{"old": normalize_port(old[0]), "target": target},
            {"old": normalize_port(old[1]), "target": target}]
    assert validate_rows(rows) is not None


def test_normalize_canvas_port():
    canvas_port = {"port_id": 7, "port_name": "Audio In L", "port_mode": 1, "port_type": 1,
                   "is_alternate": False}
    normalized = normalize_port(canvas_port)
    assert normalized["key"] == 7
    assert normalized["name"] == "Audio In L"
    assert normalized["mode"] == MODE_IN and normalized["kind"] == KIND_AUDIO


def main():
    test_exact_name_wins()
    test_channel_fallback_and_event()
    test_direction_and_kind_never_mix()
    test_role_mode_and_resolution()
    test_duplicate_output_target_is_rejected()
    test_normalize_canvas_port()
    print("rewire: all checks passed")


if __name__ == "__main__":
    main()
