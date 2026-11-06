#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Log capture must never leak ANSI codes into history or the UI.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from qt_compat import QCoreApplication

app = QCoreApplication.instance() or QCoreApplication([])

from carla_logger import (
    CarlaLogger,
    LEVEL_NAMES,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_WARNING,
)


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




def test_assertion_failure_stays_an_error():
    log = CarlaLogger()
    log.log_raw_string('Carla assertion failure: "size > 0" in file x.cpp, line 1')
    assert log.history[-1].level == LOG_LEVEL_ERROR, LEVEL_NAMES.get(log.history[-1].level)



def test_sfizz_mapping_is_debug():
    log = CarlaLogger()
    log.log_raw_string("[carla] Mapping absolutePath '/tmp/sfizz/x.sfz' relative to targetDir '/tmp/sfizz'")
    entry = log.history[-1]
    assert entry.level == LOG_LEVEL_DEBUG, LEVEL_NAMES.get(entry.level)
    assert entry.message.startswith("Mapping absolutePath")



def test_sfizz_abstract_path_is_debug():
    log = CarlaLogger()
    log.log_raw_string("[carla] Mapping abstractPath 'DefaultInstrument.sfz' relative to targetDir '/tmp/sfizz/sfizz'")
    entry = log.history[-1]
    assert entry.level == LOG_LEVEL_DEBUG, LEVEL_NAMES.get(entry.level)
    assert "[carla]" not in entry.message


def test_carla_prefix_in_the_middle_is_removed():
    log = CarlaLogger()
    log.log_raw_string("Mapping abso[carla] carla_lv2_midnam_update")
    assert "[carla]" not in log.history[-1].message


def test_repeated_assertions_are_collapsed():
    log = CarlaLogger()
    msg = 'Carla assertion failure: "size > 0" in file x.cpp, line 1'
    log.log_raw_string(msg)
    log.log_raw_string(msg)
    assert len(log.history) == 1
    last, count = next(iter(log._assertion_seen.values()))
    log._assertion_seen[next(iter(log._assertion_seen))] = (0.0, count)
    log.log_raw_string(msg)
    assert "repeats suppressed" in log.history[-1].message



def test_sfizz_clear_failure_is_debug():
    log = CarlaLogger()
    log.log_raw_string("[sfizz] Loading failed")
    assert log.history[-1].level == LOG_LEVEL_DEBUG



def test_lilv_duplicate_bundle_warning_is_debug():
    log = CarlaLogger()
    log.log_raw_string("lilv_world_add_plugin(): warning: ... found in file:///home/a/.lv2/sfizz.lv2/")
    assert log.history[-1].level == LOG_LEVEL_DEBUG

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("logger: all checks passed")
