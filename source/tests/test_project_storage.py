#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

"""Round-trip checks for project_storage (the code that touches every session file).

Run with: python3 source/tests/test_project_storage.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from project_storage import ProjectStorageManager

CARXP = """<?xml version='1.0' encoding='UTF-8'?>
<CARLA-PROJECT VERSION='2.0'>
  <EngineSettings>
    <PreferPluginBridges>false</PreferPluginBridges>
  </EngineSettings>
  <Plugin>
    <Info>
      <Name>Test Plugin</Name>
      <URI>urn:test</URI>
    </Info>
    <Parameters>
      <Parameter id="0">1.5</Parameter>
    </Parameters>
  </Plugin>
  <CanvasPositions infinite_canvas="true">
    <Position name="A" pos1x="10" pos1y="20" pos2x="0" pos2y="0" split="0" color="#ff0000"/>
  </CanvasPositions>
</CARLA-PROJECT>
"""


def _write(path, text=CARXP):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def test_xml_positions_roundtrip(storage, tmp):
    path = _write(os.path.join(tmp, "a.carxp"))
    positions = [{"name": "Node", "pos1x": 5, "pos1y": 6, "pos2x": 0, "pos2y": 0,
                  "split": False, "color": "#00ff00", "hide_unconnected_ports": True}]
    assert storage.save_canvas_positions(path, positions, {"split_view_enabled": True,
                                                           "split_view_sizes": [100, 200]}) is True
    assert not os.path.exists(path + ".tmp"), "atomic save left a temp file behind"
    loaded = storage.load_canvas_positions(path)
    assert len(loaded) == 1 and loaded[0]["name"] == "Node"
    assert loaded[0]["pos1x"] == 5 and loaded[0]["hide_unconnected_ports"] is True
    assert getattr(loaded, "split_view_sizes") == [100, 200]
    assert getattr(loaded, "infinite_canvas") is True


def test_json_save_preserves_plugin_data(storage, tmp):
    source = _write(os.path.join(tmp, "b.carxp"))
    target = os.path.join(tmp, "b.carjp")

    backend_target, is_temp = storage.prepare_for_backend_save(target)
    assert is_temp and backend_target.endswith(".carxp")
    _write(backend_target)  # stand-in for what the C++ backend would write

    assert storage.finalize_from_backend_save(target, backend_target) is True
    assert not os.path.exists(backend_target), "temp XML was not cleaned up"

    root = storage.get_project_root(target)
    assert root is not None
    assert root.find("Plugin/Info/Name").text == "Test Plugin"
    assert root.find("Plugin/Parameters/Parameter").text == "1.5"

    positions = [{"name": "P", "pos1x": 1, "pos1y": 2, "pos2x": 0, "pos2y": 0, "split": False}]
    assert storage.save_canvas_positions(target, positions) is True
    assert storage.load_canvas_positions(target)[0]["name"] == "P"


def test_json_load_temp_is_not_in_project_dir(storage, tmp):
    source = _write(os.path.join(tmp, "c.carxp"))
    target = os.path.join(tmp, "c.carjp")
    backend_target, _ = storage.prepare_for_backend_save(target)
    _write(backend_target)
    assert storage.finalize_from_backend_save(target, backend_target) is True

    load_path = storage.prepare_for_backend_load(target)
    try:
        assert os.path.exists(load_path)
        assert os.path.dirname(os.path.abspath(load_path)) != os.path.abspath(tmp), \
            "temp file must live in the system temp dir (read-only project folders)"
    finally:
        os.remove(load_path)


def test_failed_save_is_reported(storage, tmp):
    target = os.path.join(tmp, "d.carjp")
    assert storage.finalize_from_backend_save(target, os.path.join(tmp, "missing.carxp")) is False


def test_save_dialog_offers_xml_only(storage):
    save_filter = storage.save_filter("project")
    assert ".carxp" in save_filter and ".carjp" not in save_filter
    assert ".carjp" in storage.open_filter(), "legacy JSON projects must stay openable"
    assert storage.default_extension("project") == ".carxp"


def main():
    storage = ProjectStorageManager()
    with tempfile.TemporaryDirectory() as tmp:
        test_xml_positions_roundtrip(storage, tmp)
        test_json_save_preserves_plugin_data(storage, tmp)
        test_json_load_temp_is_not_in_project_dir(storage, tmp)
        test_failed_save_is_reported(storage, tmp)
    test_save_dialog_offers_xml_only(storage)
    print("project_storage: all checks passed")


if __name__ == "__main__":
    main()
