#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from sfizz_compat import ensure_sfizz_compat


def test_recreates_sfizz_layout():
    with tempfile.TemporaryDirectory() as tmp:
        home = os.path.join(tmp, "home")
        lv2 = os.path.join(tmp, "lv2")
        samples = os.path.join(home, ".sf2", "Piano", "48khz24bit")
        for path in (os.path.join(home, "sfizz", "sfizz"), lv2, samples):
            os.makedirs(path, exist_ok=True)
        open(os.path.join(home, "sfizz", "sfizz", "User.sfz"), "w").close()
        open(os.path.join(lv2, "DefaultInstrument.sfz"), "w").close()
        open(os.path.join(lv2, "DefaultScale.scl"), "w").close()
        open(os.path.join(samples, "a.wav"), "w").close()
        root = os.path.join(tmp, "sfizz-root")

        created = ensure_sfizz_compat(root=root, home=home, lv2_dir=lv2, samples_dir=samples)
        assert os.path.islink(os.path.join(root, "sfizz", "User.sfz"))
        assert os.path.islink(os.path.join(root, "sfizz", "DefaultInstrument.sfz"))
        assert os.path.islink(os.path.join(root, "sfizz", "DefaultScale.scl"))
        assert os.path.islink(os.path.join(root, "48khz24bit"))
        assert os.path.realpath(os.path.join(root, "48khz24bit")) == os.path.realpath(samples)
        assert len(created) == 4

        # Idempotent: a second pass neither duplicates nor throws.
        assert ensure_sfizz_compat(root=root, home=home, lv2_dir=lv2, samples_dir=samples) == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("sfizz_compat: all checks passed")
