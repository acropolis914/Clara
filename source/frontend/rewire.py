#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Port matching for in-place plugin replacement. Pure Python, no Qt.

MODE_IN = "in"
MODE_OUT = "out"

KIND_AUDIO = "audio"
KIND_MIDI = "midi"
KIND_CV = "cv"
KIND_PARAM = "param"
KIND_OTHER = "other"

_TYPE_TO_KIND = {
    1: KIND_AUDIO,   # PORT_TYPE_AUDIO_JACK
    2: KIND_MIDI,    # PORT_TYPE_MIDI_JACK
    3: KIND_MIDI,    # PORT_TYPE_MIDI_ALSA
    4: KIND_PARAM,   # PORT_TYPE_PARAMETER
}
_MODE_TO_STR = {1: MODE_IN, 2: MODE_OUT}


def kind_from_type(port_type):
    return _TYPE_TO_KIND.get(port_type, KIND_OTHER)


def mode_from_value(port_mode):
    return _MODE_TO_STR.get(port_mode, MODE_IN)


def normalize_port(port):
    """Accept a normalized dict, a plain dict, or a canvas port object."""
    if isinstance(port, dict):
        if isinstance(port.get("mode"), str) and "kind" in port:
            return dict(port)
        return {
            "key": port.get("port_id", port.get("key")),
            "name": port.get("port_name", port.get("name", "")),
            "mode": mode_from_value(port.get("port_mode", 0)),
            "kind": kind_from_type(port.get("port_type", 0)),
            "index": port.get("index", 0),
            "alternate": bool(port.get("is_alternate", False)),
        }
    mode = getattr(port, "mode", None)
    kind = getattr(port, "kind", None)
    if isinstance(mode, str) and kind is not None:
        return {
            "key": getattr(port, "key", None),
            "name": getattr(port, "name", ""),
            "mode": mode,
            "kind": kind,
            "index": getattr(port, "index", 0),
            "alternate": bool(getattr(port, "alternate", False)),
        }
    return {
        "key": getattr(port, "port_id", getattr(port, "key", None)),
        "name": getattr(port, "port_name", getattr(port, "name", "")),
        "mode": mode_from_value(getattr(port, "port_mode", 0)),
        "kind": kind_from_type(getattr(port, "port_type", 0)),
        "index": getattr(port, "index", 0),
        "alternate": bool(getattr(port, "is_alternate", False)),
    }


def _with_index(ports):
    counters = {}
    result = []
    for port in ports:
        port = normalize_port(port)
        bucket = (port["mode"], port["kind"])
        index = counters.get(bucket, 0)
        counters[bucket] = index + 1
        port = dict(port)
        port["index"] = index
        result.append(port)
    return result


def _role_label(mode, kind, index):
    direction = "In" if mode == MODE_IN else "Out"
    if kind == KIND_AUDIO:
        return "Audio %s #%i" % (direction, index + 1)
    if kind == KIND_MIDI:
        return "Event %s" % direction
    if kind == KIND_CV:
        return "CV %s #%i" % (direction, index + 1)
    if kind == KIND_PARAM:
        return "Parameter %s #%i" % (direction, index + 1)
    return "%s %s #%i" % (kind.title(), direction, index + 1)


def role_target(port):
    port = normalize_port(port)
    return {
        "role": (port["mode"], port["kind"], port["index"]),
        "label": _role_label(port["mode"], port["kind"], port["index"]),
    }


def actual_target(port):
    port = normalize_port(port)
    return {
        "name": port["name"],
        "mode": port["mode"],
        "kind": port["kind"],
        "index": port["index"],
        "label": port["name"],
    }


def _compatible(old, new):
    return old["mode"] == new["mode"] and old["kind"] == new["kind"]


def _pick_exact(old, candidates, used):
    for new in candidates:
        if new["key"] in used:
            continue
        if _compatible(old, new) and old["name"].casefold() == new["name"].casefold():
            return new, "name", 1.0
    return None, None, 0.0


def _pick_index(old, candidates, used):
    for new in candidates:
        if new["key"] in used:
            continue
        if _compatible(old, new) and new["index"] == old["index"]:
            return new, "channel", 0.8
    return None, None, 0.0


def match_ports(old_ports, new_ports=None):
    """Rows of {old, target, reason, confidence}.

    new_ports=None means the replacement has not been loaded yet: targets are
    role descriptors (mode/kind/index) resolved after the plugin arrives.
    """
    old_ports = _with_index(old_ports)
    if new_ports is None:
        return [
            {
                "old": port,
                "target": role_target(port),
                "reason": "role",
                "confidence": 0.6,
            }
            for port in old_ports
        ]

    new_ports = _with_index(new_ports)
    used = set()
    rows = []
    pending = []

    # Pass 1: exact names (all kinds).
    for old in old_ports:
        new, reason, confidence = _pick_exact(old, new_ports, used)
        if new is not None:
            used.add(new["key"])
            rows.append({"old": old, "target": actual_target(new), "reason": reason, "confidence": confidence})
        else:
            pending.append(old)

    # Pass 2: channel / event / CV index.
    unmatched = []
    for old in pending:
        new, reason, confidence = _pick_index(old, new_ports, used)
        if new is not None:
            used.add(new["key"])
            rows.append({"old": old, "target": actual_target(new), "reason": reason, "confidence": confidence})
        else:
            unmatched.append(old)

    for old in unmatched:
        rows.append({"old": old, "target": None, "reason": "none", "confidence": 0.0})

    order = {(MODE_IN, KIND_AUDIO): 0, (MODE_IN, KIND_MIDI): 1, (MODE_IN, KIND_CV): 2,
             (MODE_IN, KIND_PARAM): 3, (MODE_IN, KIND_OTHER): 4,
             (MODE_OUT, KIND_AUDIO): 5, (MODE_OUT, KIND_MIDI): 6, (MODE_OUT, KIND_CV): 7,
             (MODE_OUT, KIND_PARAM): 8, (MODE_OUT, KIND_OTHER): 9}
    rows.sort(key=lambda row: (order.get((row["old"]["mode"], row["old"]["kind"]), 99),
                               row["old"]["index"], row["old"]["name"].casefold()))
    return rows


def resolve_target(target, new_ports):
    """Turn a dialog target into an actual new port, or None."""
    if not target:
        return None
    new_ports = _with_index(new_ports)
    if "role" in target:
        mode, kind, index = target["role"]
        for new in new_ports:
            if new["mode"] == mode and new["kind"] == kind and new["index"] == index:
                return new
        return None
    # Exact target: name first, then the role index recorded at match time.
    mode = target.get("mode", MODE_IN)
    kind = target.get("kind", KIND_OTHER)
    name = target.get("name", "")
    for new in new_ports:
        if new["mode"] == mode and new["kind"] == kind and new["name"].casefold() == name.casefold():
            return new
    index = target.get("index", 0)
    for new in new_ports:
        if new["mode"] == mode and new["kind"] == kind and new["index"] == index:
            return new
    return None


def is_compatible(old, target):
    if not target:
        return False
    if "role" in target:
        mode, kind, _index = target["role"]
        return old["mode"] == mode and old["kind"] == kind
    return old["mode"] == target.get("mode") and old["kind"] == target.get("kind")


def validate_rows(rows):
    """Return an error string, or None when the plan can be applied."""
    used_outputs = {}
    for row in rows:
        target = row.get("target")
        if not target:
            continue
        old = row["old"]
        key = target.get("role") or (target.get("mode"), target.get("kind"), target.get("name", "").casefold())
        if old["mode"] == MODE_OUT:
            other = used_outputs.get(key)
            if other is not None:
                return "Outputs %r and %r both map to the same port" % (other, old["name"])
            used_outputs[key] = old["name"]
    return None
