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
        for path in (os.path.join(home, "sfizz", "sfizz"), lv2):
            os.makedirs(path, exist_ok=True)
        open(os.path.join(home, "sfizz", "sfizz", "User.sfz"), "w").close()
        open(os.path.join(lv2, "DefaultInstrument.sfz"), "w").close()
        open(os.path.join(lv2, "DefaultScale.scl"), "w").close()
        root = os.path.join(tmp, "sfizz-root")

        created = ensure_sfizz_compat(root=root, home=home, lv2_dir=lv2)
        assert os.path.islink(os.path.join(root, "sfizz", "User.sfz"))
        assert os.path.islink(os.path.join(root, "sfizz", "DefaultInstrument.sfz"))
        assert os.path.islink(os.path.join(root, "sfizz", "DefaultScale.scl"))
        assert len(created) == 3

        # Idempotent: a second pass neither duplicates nor throws.
        assert ensure_sfizz_compat(root=root, home=home, lv2_dir=lv2) == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("sfizz_compat: all checks passed")
