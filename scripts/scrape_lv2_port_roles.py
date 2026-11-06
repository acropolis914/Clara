#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Rebuild source/frontend/lv2_port_roles.json from the installed LV2 plugins.

Requires lv2ls and lv2info (lilv-utils). Each URI gets role lists for
audio_in, audio_out, midi_in, midi_out, cv_in and cv_out, in port order.
Audio roles are "ch:N" (main channel N, 0-based) or "sc:N" (sidechain N).
MIDI is "event", CV is "cv:N". Parameters are ignored.

Run from the repository root:
    python3 scripts/scrape_lv2_port_roles.py
"""

import argparse
import json
import os
import re
import subprocess
import sys


def parse(uri):
    out = subprocess.run(["lv2info", uri], capture_output=True, text=True, timeout=10).stdout
    name = re.search(r"^\s*Name:\s*(.+)$", out, re.M)
    heads = list(re.finditer(r"\n\tPort (\d+):\n", out))
    ports = []
    for i, head in enumerate(heads):
        chunk = out[head.end(): heads[i + 1].start() if i + 1 < len(heads) else len(out)]
        types = re.findall(r"#(AudioPort|ControlPort|AtomPort|CVPort|InputPort|OutputPort)\b", chunk)
        if "InputPort" not in types and "OutputPort" not in types:
            continue
        if "AudioPort" in types:
            kind = "audio"
        elif "AtomPort" in types:
            kind = "midi"
        elif "CVPort" in types:
            kind = "cv"
        else:
            continue
        pname = re.search(r"\bName:\s*(.+)$", chunk, re.M)
        group = re.search(r"\bGroup:\s*(\S+)", chunk)
        design = re.search(r"\bDesignation:\s*(\S+)", chunk)
        ports.append({
            "name": pname.group(1).strip() if pname else "",
            "direction": "in" if "InputPort" in types else "out",
            "kind": kind,
            "group": group.group(1).split("#")[-1] if group else "",
            "designation": design.group(1).split("#")[-1] if design else "",
        })
    return name.group(1).strip() if name else uri, ports


def explicit_channel(name, designation):
    if designation:
        value = designation.lower()
        if "side" in value and "left" in value:
            return 0
        if "side" in value and "right" in value:
            return 1
        if "left" in value:
            return 0
        if "right" in value:
            return 1
        if "center" in value or "centre" in value:
            return 2
        if "lfe" in value or "low frequency" in value:
            return 3
    text = re.sub(r"[_\-.]+", " ", (name or "").lower()).strip()
    if re.search(r"\b(left)\b|\bfl\b|\bfront left\b", text):
        return 0
    if re.search(r"\b(right)\b|\bfr\b|\bfront right\b", text):
        return 1
    if re.search(r"\b(center|centre)\b", text):
        return 2
    if re.search(r"\blfe\b|\bsub\b", text):
        return 3
    if re.search(r"\b(side left|sl)\b", text):
        return 4
    if re.search(r"\b(side right|sr)\b", text):
        return 5
    if re.search(r"(?:^|in|out|input|output)[ _-]?l$", text):
        return 0
    if re.search(r"(?:^|in|out|input|output)[ _-]?r$", text):
        return 1
    match = re.search(r"(?:^|in|out|input|output)[ _-]?(\d+)$", text)
    if match:
        return max(0, int(match.group(1)) - 1)
    return None


def is_sidechain(name, group):
    text = ((name or "") + " " + (group or "")).lower()
    return bool(re.search(r"side\s*chain|sidechain|\bsc\b|\bkey\b|external|\bext\b", text))


def roles_for(items):
    if not items:
        return None
    kind = items[0]["kind"]
    if kind == "midi":
        return ["event"] * len(items)
    if kind == "cv":
        return ["cv:%i" % i for i in range(len(items))]
    total = len(items)
    normal = side = 0
    roles = []
    for port in items:
        sc = is_sidechain(port["name"], port["group"])
        channel = explicit_channel(port["name"], port["designation"])
        if total == 1 and channel is None:
            channel = 0
        elif channel is None:
            channel = side if sc else normal
        roles.append(("sc:%i" if sc else "ch:%i") % channel)
        if sc:
            side += 1
        else:
            normal += 1
    if len(set(roles)) < len(roles):
        # Repeated names (mixer buses, duplicated channel labels): position wins.
        roles = [("sc:%i" if is_sidechain(p["name"], p["group"]) else "ch:%i") % i
                 for i, p in enumerate(items)]
    return roles


def main():
    uris = subprocess.run(["lv2ls"], capture_output=True, text=True, timeout=60).stdout.split()
    catalog = {}
    for uri in uris:
        try:
            name, ports = parse(uri)
        except Exception as exc:
            print("skip %s: %s" % (uri, exc), file=sys.stderr)
            continue
        grouped = {}
        for port in ports:
            grouped.setdefault((port["kind"], port["direction"]), []).append(port)
        buckets = {}
        for (kind, direction), items in grouped.items():
            roles = roles_for(items)
            if roles:
                buckets[kind + "_" + direction] = roles
        if buckets:
            catalog[uri] = {"n": name, **buckets}
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="write even when the plugin count drops sharply")
    args = parser.parse_args()
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "source", "frontend", "lv2_port_roles.json")
    old_count = 0
    try:
        with open(target, encoding="utf-8") as handle:
            old_count = len(json.load(handle))
    except Exception:
        pass
    if old_count and len(catalog) < old_count * 0.8 and not args.force:
        print("refusing to write: %i plugins, previous catalog had %i (use --force)"
              % (len(catalog), old_count), file=sys.stderr)
        return 1
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(catalog, handle, separators=(",", ":"))
    print("wrote %i LV2 plugins to %s" % (len(catalog), os.path.abspath(target)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
