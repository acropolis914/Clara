#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Log capture must never leak ANSI codes into history or the UI.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from qt_compat import QCoreApplication

app = QCoreApplication.instance() or QCoreApplication([])

from carla_logger import CarlaLogger, LEVEL_NAMES, LOG_LEVEL_ERROR, LOG_LEVEL_WARNING


def check(raw, level, message):
    log = CarlaLogger()
    log.log_raw_string(raw)
    entry = log.history[-1]
    assert entry.message == message, (raw, entry.message, message)
    assert "\x1b" not in entry.message, entry.message
    assert "[31m" not in entry.message and "[0m" not in entry.message, entry.message
    if level is not None:
        assert entry.level == level, (raw, LEVEL_NAMES.get(entry.level), LEVEL_NAMES.get(level))


def test_sane_codes_are_stripped():
    check("\x1b[31m[carla] boom happened\x1b[0m", LOG_LEVEL_ERROR, "boom happened")
    check("\x1b[33m[carla] careful now\x1b[0m", LOG_LEVEL_WARNING, "careful now")


def test_escaped_codes_are_stripped():
    check("[31m[carla] mangled red\x1b[0m", LOG_LEVEL_ERROR, "mangled red")


def test_plain_text_passes_through():
    check("plain line", None, "plain line")


def test_entry_messages_are_cleaned():
    entry = CarlaLogger().history
    assert entry == []
    from carla_logger import LogEntry
    assert LogEntry(LOG_LEVEL_ERROR, "PLUGIN", "[31mkeep [0mthis").message == "keep this"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("logger: all checks passed")
