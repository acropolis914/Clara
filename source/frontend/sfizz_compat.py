#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Recreate the temp layout sfizz's saved LV2 state expects.

sfizz keeps relative sfz/tuning paths in the project; Carla materialises them
under a temp root. Clearing /tmp makes those paths vanish and the instrument
fails to load. This is a best-effort shim until the project state is saved with
stable paths.
"""

import glob
import os
import tempfile


def ensure_sfizz_compat(root=None, home=None, lv2_dir=None, samples_dir=None):
    root = root or os.path.join(tempfile.gettempdir(), "sfizz")
    home = home or os.path.expanduser("~")
    lv2_dir = lv2_dir or "/usr/lib/lv2/sfizz.lv2/Contents/Resources"
    created = []

    sfizz_dir = os.path.join(root, "sfizz")
    os.makedirs(sfizz_dir, exist_ok=True)

    sources = [os.path.join(home, "sfizz", "sfizz"), lv2_dir]
    for source_dir in sources:
        if not os.path.isdir(source_dir):
            continue
        try:
            names = os.listdir(source_dir)
        except OSError:
            continue
        for name in names:
            if not name.lower().endswith((".sfz", ".scl")):
                continue
            target = os.path.join(sfizz_dir, name)
            if os.path.lexists(target):
                continue
            try:
                os.symlink(os.path.join(source_dir, name), target)
                created.append(target)
            except OSError:
                pass

    if samples_dir is None:
        candidates = glob.glob(os.path.join(home, ".sf2", "*", "48khz24bit"))
        samples_dir = candidates[0] if candidates else None
    if samples_dir and os.path.isdir(samples_dir):
        target = os.path.join(root, "48khz24bit")
        if not os.path.lexists(target):
            try:
                os.symlink(samples_dir, target)
                created.append(target)
            except OSError:
                pass

    return created
