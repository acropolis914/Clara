#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Per-node peaks for PipeWire nodes that have no PulseAudio source.
#
# Playback streams (Spotify, browsers, Electron apps) are sink-inputs: they have
# no capture source and no monitor of their own, so the PulseAudio peak-detect
# sampler cannot see them. `pw-record --target <node>` can capture a single
# node directly, so we run one tiny, short-lived process per such node and read
# its float32 peak from the pipe. Everything stays on the GUI thread.
# ------------------------------------------------------------------------------------------------------------

import os
import shutil
import struct
import subprocess
import time

RATE = 50            # samples per second; one peak per 20 ms is plenty
CHUNK = 1024         # max bytes read per node per tick
RESPAWN_DELAY = 5.0  # do not hammer a node that refuses to be captured


class PwRecordSampler(object):
    """Samples per-node peaks with `pw-record`, one process per requested node."""

    def __init__(self):
        self._procs = {}    # node name -> Popen
        self._levels = {}   # node name -> raw peak 0.0 - 1.0
        self._held = {}     # node name -> peak-hold level
        self._held_at = {}  # node name -> monotonic time of last hold
        self._failed = {}   # node name -> monotonic time of last failure
        self._available = None

    # -- lifecycle -------------------------------------------------------------------------------------------

    def is_available(self):
        if self._available is None:
            self._available = shutil.which("pw-record") is not None
        return self._available

    def is_running(self):
        return bool(self._procs)

    def start(self):
        return self.is_available()

    def stop(self):
        for name in list(self._procs):
            self._kill(name)
        self._levels.clear()
        self._held.clear()
        self._held_at.clear()
        self._failed.clear()

    def set_nodes(self, names):
        # never sample our own capture clients, or they spawn each other forever
        wanted = {n for n in names if n and not n.lower().startswith("pw-record")}
        for name in list(self._procs):
            if name not in wanted:
                self._kill(name)
        for name in wanted:
            if name not in self._procs:
                self._spawn(name)
        for name in list(self._levels):
            if name not in wanted:
                self._levels.pop(name, None)
                self._held.pop(name, None)

    # -- reading ---------------------------------------------------------------------------------------------

    def process(self):
        for name, proc in list(self._procs.items()):
            if proc.poll() is not None:
                self._kill(name)
                self._failed[name] = time.monotonic()
                continue
            try:
                data = os.read(proc.stdout.fileno(), CHUNK)
            except (BlockingIOError, InterruptedError):
                continue
            except OSError:
                self._kill(name)
                self._failed[name] = time.monotonic()
                continue
            if not data:
                continue
            count = len(data) // 4
            if count <= 0:
                continue
            try:
                peak = max(abs(v) for v in struct.unpack("<%df" % count, data[:count * 4]))
            except Exception:
                continue
            self._levels[name] = min(1.0, peak)

    def level_for(self, name):
        if not name:
            return 0.0

        now = time.monotonic()
        raw = self._levels.get(name, 0.0)
        held = self._held.get(name, 0.0)
        last = self._held_at.get(name, now)

        if raw >= held:
            held = raw
            self._held_at[name] = now
        elif now - last > 0.15:
            held = max(raw, held * (0.85 ** ((now - last - 0.15) / 0.04)))
            if held < 0.005:
                held = 0.0

        self._held[name] = held
        return held

    # -- processes -------------------------------------------------------------------------------------------

    def _spawn(self, name):
        failed_at = self._failed.get(name)
        if failed_at is not None and time.monotonic() - failed_at < RESPAWN_DELAY:
            return
        if not self.is_available():
            return
        try:
            proc = subprocess.Popen(
                [
                    "pw-record",
                    "--target", name,
                    "--rate", str(RATE),
                    "--channels", "1",
                    "--format", "f32",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
            os.set_blocking(proc.stdout.fileno(), False)
            self._procs[name] = proc
        except Exception:
            self._failed[name] = time.monotonic()

    def _kill(self, name):
        proc = self._procs.pop(name, None)
        self._levels.pop(name, None)
        self._held.pop(name, None)
        if proc is None:
            return
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=0.2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


_sampler = None


def get_sampler():
    global _sampler
    if _sampler is None:
        _sampler = PwRecordSampler()
    return _sampler
