#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Drive a scratch Clara instance through claramsg and check the UI still works.

This is the loop we used to run by hand: start the app, wait for it, change a
setting, switch theme, zoom the canvas, take a screenshot, quit. It runs under
its own CLARA_INSTANCE_KEY, so it never touches the user's running instance,
and it restores any setting it changes.

    python3 scripts/ui_smoke.py
    python3 scripts/ui_smoke.py --project /path/to/project.carjp
    python3 scripts/ui_smoke.py --keep-open   # leave the app running to inspect
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "source", "frontend")
CLARAMSG = os.path.join(FRONTEND, "claramsg")
INSTANCE_KEY = "ui-smoke"


class SmokeError(Exception):
    pass


class Smoke(object):
    def __init__(self, project=None, verbose=False, keep_open=False):
        self.project = project
        self.verbose = verbose
        self.keep_open = keep_open
        self.env = dict(os.environ)
        self.env["CLARA_INSTANCE_KEY"] = INSTANCE_KEY
        self.proc = None
        self.tmpdir = tempfile.mkdtemp(prefix="clara-ui-smoke-")
        self.original = {}

    # -- helpers ---------------------------------------------------------

    def claramsg(self, *args, check=True):
        cmd = [sys.executable, CLARAMSG] + [str(arg) for arg in args]
        # The GUI thread can be busy right after a theme/settings apply; one
        # retry covers that without sleeping blindly.
        result = None
        for attempt in range(2):
            result = subprocess.run(cmd, cwd=FRONTEND, env=self.env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=60)
            if result.returncode == 0 or attempt == 1:
                break
            time.sleep(0.8)
        if self.verbose:
            print("$ claramsg %s -> %s" % (" ".join(str(a) for a in args),
                                           result.stdout.strip()))
        if check and result.returncode != 0:
            raise SmokeError("claramsg %s failed: %s" % (
                " ".join(str(a) for a in args), result.stdout.strip()))
        return result.stdout.strip()

    def setting(self, field):
        return self.claramsg("settings", "get", field)

    def assert_equal(self, label, actual, expected):
        if str(actual).strip() != str(expected).strip():
            raise SmokeError("%s: expected %r, got %r" % (label, expected, actual))
        print("ok   %s" % label)

    def assert_true(self, label, condition, detail=""):
        if not condition:
            raise SmokeError("%s%s" % (label, (": " + detail) if detail else ""))
        print("ok   %s" % label)

    # -- lifecycle -------------------------------------------------------

    def start(self):
        # Any stale scratch instance from a previous run.
        self.claramsg("quit", "--force", check=False)
        time.sleep(0.3)
        cmd = [sys.executable, "./carla", "--debug", "debug"]
        if self.project:
            cmd.append(os.path.abspath(self.project))
        self.proc = subprocess.Popen(cmd, cwd=FRONTEND, env=self.env,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     start_new_session=True)
        self.claramsg("wait", "--ready", "--timeout", "90")
        print("ok   app ready (pid %s)" % self.proc.pid)

    def stop(self):
        self.claramsg("quit", "--force", check=False)
        if self.proc is not None:
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()

    # -- checks ----------------------------------------------------------

    def snapshot_settings(self):
        self.claramsg("settings", "open")
        self.claramsg("wait", "--dialog", "--timeout", "20")
        for field in ("app_theme", "shadow_spread"):
            self.original[field] = self.setting(field)

    def restore_settings(self):
        for field, value in self.original.items():
            self.claramsg("settings", "set", field, value, check=False)
        self.claramsg("settings", "apply", check=False)

    def check_shadows(self):
        self.claramsg("settings", "page", "Patchbay")
        current = self.setting("shadow_spread")
        self.assert_true("shadow spread is readable", current.lstrip("-").isdigit(), current)
        self.claramsg("settings", "set", "shadow_spread", "9")
        state = self.claramsg("canvas", "state", "-j")
        live = json.loads(state)["canvas"]["shadow_spread"]
        self.assert_equal("shadow spread previews live", live, 9)
        self.claramsg("settings", "apply")
        self.assert_equal("shadow spread survives apply", self.setting("shadow_spread"), "9")

    def check_canvas(self):
        self.assert_equal("canvas zoom 0.5", self.claramsg("canvas", "zoom", "0.5"), "0.5")
        self.assert_equal("canvas zoom reset", self.claramsg("canvas", "zoom", "reset"), "1.0")
        state = json.loads(self.claramsg("canvas", "state", "-j"))["canvas"]
        if self.project:
            self.assert_true("canvas has nodes", state.get("nodes", 0) > 0, str(state))
        self.assert_true("shadows are enabled", bool(state.get("box_shadows")))

    def check_screenshot(self):
        path = os.path.join(self.tmpdir, "smoke.png")
        self.claramsg("shot", path)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        self.assert_true("screenshot written", size > 20000, "%d bytes" % size)
        return path

    def check_theme(self):
        self.claramsg("settings", "page", "General")
        self.claramsg("settings", "set", "app_theme", "Clara Light")
        self.claramsg("settings", "apply")
        self.assert_equal("theme switch persisted", self.setting("app_theme"), "Clara Light")
        self.assert_equal("instance still responds after theme switch",
                          self.claramsg("status").splitlines()[0].split()[-1],
                          str(self.proc.pid))

    # -- main ------------------------------------------------------------

    def run(self):
        try:
            self.start()
            self.snapshot_settings()
            self.check_shadows()
            self.check_canvas()
            shot = self.check_screenshot()
            self.check_theme()
            print("shot %s" % shot)
        finally:
            try:
                self.restore_settings()
            except Exception as exc:  # noqa: BLE001 - best effort, never mask the real error
                print("warn could not restore settings: %s" % exc)
            if not self.keep_open:
                self.stop()
            else:
                print("app left running (pid %s)" % (self.proc.pid if self.proc else "?"))


def main():
    parser = argparse.ArgumentParser(description="Clara UI smoke test via claramsg")
    parser.add_argument("--project", default=None, help="project to open")
    parser.add_argument("--keep-open", action="store_true", help="leave the app running")
    parser.add_argument("--verbose", action="store_true", help="print every claramsg call")
    args = parser.parse_args()

    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("ui_smoke: no display, skipping")
        return 0

    smoke = Smoke(args.project, args.verbose, args.keep_open)
    try:
        smoke.run()
    except SmokeError as exc:
        print("FAIL %s" % exc)
        return 1
    finally:
        shutil.rmtree(smoke.tmpdir, ignore_errors=True)
    print("ui_smoke: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
