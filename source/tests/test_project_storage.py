#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

"""Round-trip checks for project_storage (the code that touches every session file).

Run with: python3 source/tests/test_project_storage.py
"""

import json
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

CARJP = {
    "format": "carla-project-json",
    "version": "1.0",
    "CARLA-PROJECT": {
        "@attributes": {"VERSION": "2.0"},
        "EngineSettings": {"PreferPluginBridges": "false"},
        "Plugin": {
            "Info": {"Name": "Test Plugin", "URI": "urn:test"},
            "Parameters": {"Parameter": [{"@attributes": {"id": "0"}, "#text": "1.5"}]},
        },
    },
}


def _write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _write_json(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent="\t")
    return path


def test_xml_positions_roundtrip(storage, tmp):
    path = _write_text(os.path.join(tmp, "a.carxp"), CARXP)
    positions = [{"name": "Node", "pos1x": 5, "pos1y": 6, "pos2x": 0, "pos2y": 0,
                  "split": False, "color": "#00ff00", "hide_unconnected_ports": True,
                  "left": ["out_L", "out_R"], "right": ["in_L"],
                  "port_modes": {"out_L": 2, "in_L": 1}, "port_types": {"out_L": 1, "in_L": 2},
                  "width": 202, "height": 107}]
    assert storage.save_canvas_positions(path, positions, {"split_view_enabled": True,
                                                           "split_view_sizes": [100, 200]}) is True
    assert not os.path.exists(path + ".tmp"), "atomic save left a temp file behind"
    loaded = storage.load_canvas_positions(path)
    assert len(loaded) == 1 and loaded[0]["name"] == "Node"
    assert loaded[0]["pos1x"] == 5 and loaded[0]["hide_unconnected_ports"] is True
    assert loaded[0]["left"] == ["out_L", "out_R"] and loaded[0]["right"] == ["in_L"]
    assert loaded[0]["port_types"] == {"out_L": 1, "in_L": 2}
    assert loaded[0]["width"] == 202 and loaded[0]["height"] == 107
    assert getattr(loaded, "split_view_sizes") == [100, 200]
    assert getattr(loaded, "infinite_canvas") is True


def test_json_positions_keep_engine_data(storage, tmp):
    path = _write_json(os.path.join(tmp, "b.carjp"), CARJP)

    root = storage.get_project_root(path)
    assert root is not None
    assert root.find("Plugin/Info/Name").text == "Test Plugin"

    positions = [{"name": "P", "pos1x": 1, "pos1y": 2, "pos2x": 0, "pos2y": 0, "split": False,
                  "left": ["out_L"], "right": ["in_L", "in_R"],
                  "port_modes": {"out_L": 2, "in_L": 1}, "port_types": {"out_L": 1, "in_L": 2},
                  "width": 158, "height": 83}]
    assert storage.save_canvas_positions(path, positions) is True
    assert not os.path.exists(path + ".tmp"), "atomic save left a temp file behind"
    loaded = storage.load_canvas_positions(path)
    assert loaded[0]["name"] == "P"
    assert loaded[0]["left"] == ["out_L"] and loaded[0]["right"] == ["in_L", "in_R"]
    assert loaded[0]["port_types"] == {"out_L": 1, "in_L": 2}
    assert loaded[0]["width"] == 158 and loaded[0]["height"] == 83

    # engine-owned data must survive the frontend position write
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["CARLA-PROJECT"]["Plugin"]["Info"]["Name"] == "Test Plugin"


def test_json_load_needs_no_conversion(storage, tmp):
    path = _write_json(os.path.join(tmp, "c.carjp"), CARJP)
    assert storage.prepare_for_backend_load(path) == path, "the engine reads .carjp directly"


def test_force_bridged_json_copy(storage, tmp):
    path = _write_json(os.path.join(tmp, "d.carjp"), CARJP)
    patched = storage.prepare_for_backend_load(path, force_bridged=True)
    try:
        assert patched != path and os.path.exists(patched)
        assert os.path.dirname(os.path.abspath(patched)) != os.path.abspath(tmp)
        with open(patched, encoding="utf-8") as f:
            doc = json.load(f)
        assert doc["CARLA-PROJECT"]["EngineSettings"]["PreferPluginBridges"] == "true"
        with open(path, encoding="utf-8") as f:
            assert json.load(f)["CARLA-PROJECT"]["EngineSettings"]["PreferPluginBridges"] == "false"
    finally:
        os.remove(patched)


def test_new_saves_default_to_json(storage):
    save_filter = storage.save_filter("project")
    assert save_filter.startswith("Carla JSON Project"), save_filter
    assert ".carxp" in save_filter, "XML must stay saveable for backwards compatibility"
    assert storage.default_extension("project") == ".carjp"
    assert storage.get_format_tag("song.carxp") == "xml"
    assert storage.get_format_tag("song.carjp") == "json"


def test_bridge_map_roundtrip(storage, tmp):
    path = _write_json(os.path.join(tmp, "bridge.carjp"), CARJP)
    positions = [{"name": "A", "pos1x": 1, "pos1y": 2, "pos2x": 0, "pos2y": 0, "split": False}]
    assert storage.save_canvas_positions(path, positions, {"bridge_plugins": [1, 3]}) is True
    loaded = storage.load_canvas_positions(path)
    assert getattr(loaded, "bridge_plugins", None) == [1, 3]

    xml_path = _write_text(os.path.join(tmp, "bridge.carxp"), CARXP)
    assert storage.save_canvas_positions(xml_path, positions, {"bridge_plugins": [0, 2]}) is True
    assert getattr(storage.load_canvas_positions(xml_path), "bridge_plugins", None) == [0, 2]


def test_prepare_for_load_sets_per_plugin_bridge(storage, tmp):
    doc = {
        "format": "carla-project-json", "version": "1.0",
        "CARLA-PROJECT": {
            "@attributes": {"VERSION": "2.6"},
            "EngineSettings": {"PreferPluginBridges": "true"},
            "Plugin": [
                {"Info": {"Name": "native"}, "Data": {"Options": "1"}},
                {"Info": {"Name": "bridged"}, "Data": {"Options": "1"}},
            ],
        },
    }
    path = _write_json(os.path.join(tmp, "prep.carjp"), doc)
    patched = storage.prepare_for_backend_load(path, bridge_plugins=[1])
    try:
        data = json.load(open(patched, encoding="utf-8"))
        project = data["CARLA-PROJECT"]
        assert project["EngineSettings"]["PreferPluginBridges"] == "false"
        assert int(project["Plugin"][0]["Data"]["Options"]) == 1
        assert int(project["Plugin"][1]["Data"]["Options"]) & 0x800
    finally:
        os.remove(patched)


def test_failed_save_is_reported(storage, tmp):
    target = os.path.join(tmp, "e.carjp")
    assert storage.finalize_from_backend_save(target, os.path.join(tmp, "missing.carjp")) is False


def main():
    storage = ProjectStorageManager()
    with tempfile.TemporaryDirectory() as tmp:
        test_xml_positions_roundtrip(storage, tmp)
        test_json_positions_keep_engine_data(storage, tmp)
        test_json_load_needs_no_conversion(storage, tmp)
        test_force_bridged_json_copy(storage, tmp)
        test_bridge_map_roundtrip(storage, tmp)
        test_prepare_for_load_sets_per_plugin_bridge(storage, tmp)
        test_failed_save_is_reported(storage, tmp)
    test_new_saves_default_to_json(storage)
    print("project_storage: all checks passed")


if __name__ == "__main__":
    main()
