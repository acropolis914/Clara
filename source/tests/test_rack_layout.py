#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""UI regression harness: launches a real Clara instance headless (Dummy audio
driver, fixture project) and asserts the rack layout invariants that
historically regressed (LED tile clipping, knob pinning, item width overflow).

Requires a working audio setup only through the Dummy driver, no JACK. Skips
when PyQt is missing or another Clara instance already holds the test key.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(HERE, "..", "frontend")
FIXTURE = os.path.join(HERE, "fixtures", "rack_probe.carxp")
INSTANCE_KEY = "ui-rack-test"
READY_TIMEOUT = 180.0

sys.path.insert(0, FRONTEND)

try:
    from PyQt6.QtCore import QCoreApplication
except ImportError:
    try:
        from PyQt5.QtCore import QCoreApplication
    except ImportError:
        QCoreApplication = None

if QCoreApplication is None:  # pragma: no cover - CI without Qt
    print("rack_layout: skipped (no Qt)")
    sys.exit(0)

_app = QCoreApplication.instance() or QCoreApplication([])

from clara_instance_core import build_request, encode_request, instance_paths  # noqa: E402
from carla_instance import MsgClient  # noqa: E402


def _send(paths, **fields):
    payload = encode_request(build_request(**fields))
    raw = MsgClient.request(paths["socket"], payload, 10000)
    if raw is None:
        return None
    reply = json.loads(raw.decode("utf-8"))
    if not reply.get("ok"):
        return None
    return reply.get("data") or {}


def _write_settings(tmp):
    """Isolated QSettings: Dummy audio driver (no JACK), fixed theme."""
    cfg = os.path.join(tmp, "falkTX")
    os.makedirs(cfg, exist_ok=True)
    lines = [
        "[Engine]",
        "AudioDriver=%s" % os.environ.get("CLARA_TEST_AUDIO_DRIVER", "PulseAudio"),
        "",
        "[Main]",
        "AppTheme=Catppuccin Macchiato",
        "ConfirmExit=false",
        "LogToConsole=true",
    ]
    with open(os.path.join(cfg, "Carla2.conf"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _wait_ready(paths, log_path):
    """Ready = socket answers and the fixture project's plugins are loaded."""
    deadline = time.time() + READY_TIMEOUT
    while time.time() < deadline:
        data = _send(paths, cmd="status")
        if data is not None and data.get("mode") == "gui" and data.get("plugins", 0) >= 3:
            return True
        time.sleep(0.5)
    return False


def _assert(cond, message, failed):
    if not cond:
        failed.append(message)
        print("FAIL: %s" % message)
    else:
        print("ok: %s" % message)


def main():
    tmp = tempfile.mkdtemp(prefix="clara-rack-test-")
    _write_settings(tmp)

    # The test process itself must resolve the same instance key as the child.
    os.environ["CLARA_INSTANCE_KEY"] = INSTANCE_KEY
    env = dict(os.environ)
    env.update({
        "CLARA_INSTANCE_KEY": INSTANCE_KEY,
        "XDG_CONFIG_HOME": tmp,
        "QT_QPA_PLATFORM": "offscreen",
        "NO_COLOR": "1",
    })

    log_path = os.path.join(tmp, "clara.log")
    with open(log_path, "wb") as log:
        proc = subprocess.Popen(
            [sys.executable, os.path.join(FRONTEND, "carla"), "--debug", "debug", FIXTURE],
            cwd=FRONTEND, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        failed = []
        try:
            paths = instance_paths()
            assert paths["key"] == INSTANCE_KEY, paths
            if not _wait_ready(paths, log_path):
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    log_head = f.read()
                if "Failed to start engine on first try" in log_head:
                    print("rack_layout: skipped (audio engine %s unavailable)" %
                          os.environ.get("CLARA_TEST_AUDIO_DRIVER", "PulseAudio"))
                    return 0
                print("rack_layout: instance did not become ready")
                return 1

            rack = _send(paths, cmd="rack", action="dump")
            assert rack is not None, "rack dump request failed"
            vw = rack["viewport"][0]
            _assert(rack["h_extent"] == 0, "no horizontal overflow in rack list", failed)
            for entry in rack["items"]:
                widget = entry["widget"]
                if widget is None:
                    continue
                _assert(widget["size"][0] <= vw + 1,
                        "row %d width %d fits viewport %d" % (entry["row"], widget["size"][0], vw),
                        failed)
                _assert(widget["size"][1] >= widget["fixed_h"] - 1,
                        "row %d height honors fixed height %s" % (entry["row"], widget["fixed_h"]),
                        failed)

            detail = _send(paths, cmd="rack", action="detail")
            assert detail is not None, "rack detail request failed"
            for entry in detail["items"]:
                widget = entry["widget"]
                if widget is None:
                    continue
                det = widget.get("detail") or {}
                # The magic numbers in getFixedHeight() must always leave room
                # for the slot's real (polished) minimums - this is the class
                # of bug that clipped LED tiles inside fixed rows.
                _assert(widget["min"][1] <= widget["fixed_h"] + 1,
                        "row %d minimum height %d fits fixed height %s" % (
                            entry["row"], widget["min"][1], widget["fixed_h"]),
                        failed)
                _assert(widget["min"][0] <= vw + 1,
                        "row %d minimum width %d fits viewport %d (wide: %s)" % (
                            entry["row"], widget["min"][0], vw,
                            ", ".join("%s#%s=%s" % (c["cls"], c["name"], c["min"][0])
                                      for c in det.get("wide_children", [])
                                      if not c["name"].startswith("qt_"))),
                        failed)
                for led in det.get("leds", []):
                    _assert(led["size"][0] == led["size"][1],
                            "row %d %s is square %s" % (entry["row"], led["attr"], led["size"]),
                            failed)
                    _assert(led["tile_prop"], "row %d %s opts out of button chrome" % (entry["row"], led["attr"]),
                            failed)
                for dial in det.get("dials", []):
                    _assert(dial["minhint"] == dial["hint"] and not dial["custom"],
                            "row %d dial un-pinned (hint %s == minhint %s)" % (entry["row"], dial["hint"], dial["minhint"]),
                            failed)
        finally:
            try:
                _send(paths, cmd="quit", force=True)
            except Exception:
                pass
            time.sleep(1.0)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
            proc.wait()

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        crash_lines = [l for l in f if "CRITICAL TRACEBACK" in l or "AttributeError" in l]
    _assert(not crash_lines, "no tracebacks in app log", failed)

    print("rack_layout: %s" % ("FAILED (%d)" % len(failed) if failed else "all checks passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
