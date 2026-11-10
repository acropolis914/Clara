#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# A canvas setting only works if its key reaches both the settings schema and
# the fSavedSettings dict that setupCanvas() reads. A key missing from the
# latter silently falls back to its default (this is how the shadow sliders
# were broken).

import os
import re

_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


def _read(name):
    with open(os.path.join(_FRONTEND, name), "r", encoding="utf-8") as f:
        return f.read()


def _setup_canvas_keys():
    text = _read("patchbay_view.py")
    start = text.index("    def setupCanvas(self):")
    end = text.index("\n    def ", start + 10)
    return set(re.findall(r"CARLA_KEY_CANVAS_[A-Z_]+", text[start:end]))


def test_canvas_keys_are_loaded():
    text = _read("settings_panel.py")
    loaded = set(re.findall(r"(CARLA_KEY_CANVAS_[A-Z_]+)(?=:)", text))
    loaded |= set(re.findall(r"fSavedSettings\[(CARLA_KEY_CANVAS_[A-Z_]+)\]", text))
    missing = sorted(_setup_canvas_keys() - loaded)
    assert not missing, (
        "canvas keys read by setupCanvas() but missing from fSavedSettings: %s" % missing)


def test_shadow_keys_are_in_the_schema():
    schema = _read("settings_schema.py")
    for key in ("CARLA_KEY_CANVAS_SHADOW_SPREAD",
                "CARLA_KEY_CANVAS_SHADOW_DISTANCE",
                "CARLA_KEY_CANVAS_SHADOW_OPACITY",
                "CARLA_KEY_CANVAS_SHADOW_DRAG"):
        assert '"key": %s' % key in schema, "%s is not in the settings schema" % key


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("settings_hookup: all checks passed")
