#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import json
import tempfile
import xml.etree.ElementTree as ET

class ProjectFormatError(Exception):
    pass

def _temp_project_path():
    """Temp XML path in the system temp dir, so loading works from read-only project folders."""
    fd, path = tempfile.mkstemp(prefix="clara_", suffix=".carxp")
    os.close(fd)
    return path

def _atomic_write_xml(tree, filepath):
    """Writes the tree via a sibling temp file, so a crash mid-write cannot truncate the project."""
    tmp_path = filepath + ".tmp"
    try:
        tree.write(tmp_path, encoding="UTF-8", xml_declaration=True)
        os.replace(tmp_path, filepath)
        return True
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise

class CanvasPositionList(list):
    """Subclass of list that allows attaching arbitrary canvas metadata attributes."""
    pass

def xml_elem_to_dict(elem):
    """Losslessly converts an XML ElementTree element into a Python dict/data structure."""
    node = {}
    if elem.attrib:
        node["@attributes"] = dict(elem.attrib)

    text = elem.text.strip() if elem.text and elem.text.strip() else None
    children = list(elem)
    if children:
        child_dict = {}
        for child in children:
            cd = xml_elem_to_dict(child)
            tag = child.tag
            if tag in child_dict:
                if not isinstance(child_dict[tag], list):
                    child_dict[tag] = [child_dict[tag]]
                child_dict[tag].append(cd)
            else:
                child_dict[tag] = cd
        if text:
            child_dict["#text"] = text
        node.update(child_dict)
    elif text:
        if elem.attrib:
            node["#text"] = text
            return node
        return text

    return node

def dict_to_xml_elem(tag, data):
    """Reconstructs an XML ElementTree element from the dictionary structure."""
    elem = ET.Element(tag)
    if isinstance(data, dict):
        if "@attributes" in data:
            for k, v in data["@attributes"].items():
                elem.set(str(k), str(v))
        if "#text" in data:
            elem.text = str(data["#text"])

        for k, v in data.items():
            if k in ("@attributes", "#text"):
                continue
            if isinstance(v, list):
                for item in v:
                    elem.append(dict_to_xml_elem(k, item))
            else:
                elem.append(dict_to_xml_elem(k, v))
    elif data is not None:
        elem.text = str(data)

    return elem


class BaseProjectHandler:
    def can_handle(self, filepath):
        raise NotImplementedError

    def load_root(self, filepath):
        """Returns an ElementTree root element for the project, or None if unreadable"""
        raise NotImplementedError

    def load_positions(self, filepath):
        raise NotImplementedError

    def save_positions(self, filepath, positions):
        raise NotImplementedError

    def load_full_project_as_xml_path(self, filepath):
        """Returns a path to an XML project file (either the file itself or a converted tmp file)"""
        raise NotImplementedError

    def save_full_project_from_xml_path(self, target_filepath, source_xml_path):
        """Saves a full project to target_filepath from source_xml_path"""
        raise NotImplementedError


class CarlaXmlProjectHandler(BaseProjectHandler):
    """Handler for Carla .carxp XML projects (100% backward compatible)"""
    def can_handle(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return False
        if filepath.lower().endswith(".carxp"):
            return True
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(256)
                return "<CARLA-PROJECT" in head
        except Exception:
            return False

    def load_root(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            return ET.parse(filepath).getroot()
        except Exception:
            return None

    def load_positions(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return []
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag != "CARLA-PROJECT":
                return []

            data_list = CanvasPositionList()
            is_infinite = False
            canvas_elem = root.find("CanvasPositions")
            split_view_enabled = None
            split_view_sizes = None
            containers_data = None
            if canvas_elem is not None:
                is_infinite = canvas_elem.get("infinite_canvas") in ("1", "true", "True")
                if "split_view_enabled" in canvas_elem.attrib:
                    split_view_enabled = canvas_elem.get("split_view_enabled") in ("1", "true", "True")
                if "split_view_sizes" in canvas_elem.attrib:
                    try:
                        split_view_sizes = [int(s) for s in canvas_elem.get("split_view_sizes").split(",") if s.strip()]
                    except Exception:
                        pass
                containers_elem = canvas_elem.find("Containers")
                if containers_elem is not None and containers_elem.text:
                    try:
                        containers_data = json.loads(containers_elem.text)
                    except Exception:
                        pass
                for p_elem in canvas_elem.findall("Position"):
                    name = p_elem.get("name", "")
                    if name:
                        data_list.append({
                            "name": name,
                            "pos1x": float(p_elem.get("pos1x", 0)),
                            "pos1y": float(p_elem.get("pos1y", 0)),
                            "pos2x": float(p_elem.get("pos2x", 0)),
                            "pos2y": float(p_elem.get("pos2y", 0)),
                            "split": p_elem.get("split") in ("1", "true", "True"),
                            "color": p_elem.get("color", ""),
                            "hide_unconnected_ports": p_elem.get("hide_unconnected_ports") in ("1", "true", "True"),
                        })

            if not data_list:
                for pb_tag in ("Patchbay", "ExternalPatchbay"):
                    pb_elem = root.find(pb_tag)
                    if pb_elem is not None:
                        pos_elem = pb_elem.find("Positions")
                        if pos_elem is not None:
                            for p_elem in pos_elem.findall("Position"):
                                name_elem = p_elem.find("Name")
                                name = name_elem.text if name_elem is not None else ""
                                if name:
                                    x1 = float(p_elem.get("x1", 0))
                                    y1 = float(p_elem.get("y1", 0))
                                    x2 = float(p_elem.get("x2", 0))
                                    y2 = float(p_elem.get("y2", 0))
                                    data_list.append({
                                        "name": name,
                                        "pos1x": x1,
                                        "pos1y": y1,
                                        "pos2x": x2,
                                        "pos2y": y2,
                                        "split": (x2 != 0 or y2 != 0),
                                        "color": p_elem.get("color", ""),
                                        "hide_unconnected_ports": False,
                                    })
            # Attach infinite_canvas and layout metadata to the returned list
            setattr(data_list, "infinite_canvas", is_infinite)
            if split_view_enabled is not None:
                setattr(data_list, "split_view_enabled", split_view_enabled)
            if split_view_sizes is not None:
                setattr(data_list, "split_view_sizes", split_view_sizes)
            if containers_data is not None:
                setattr(data_list, "patchbay_containers", containers_data)
            return data_list
        except Exception as e:
            print("CarlaXmlProjectHandler::load_positions error:", e)
            return CanvasPositionList()

    def save_positions(self, filepath, positions, extra_metadata=None):
        if not filepath or not os.path.exists(filepath):
            return False
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag != "CARLA-PROJECT":
                return False

            for child in list(root):
                if child.tag == "CanvasPositions":
                    root.remove(child)

            canvas_pos_elem = ET.SubElement(root, "CanvasPositions")
            canvas_pos_elem.set("infinite_canvas", "true")
            if extra_metadata:
                if "split_view_enabled" in extra_metadata:
                    canvas_pos_elem.set("split_view_enabled", "1" if extra_metadata["split_view_enabled"] else "0")
                if "split_view_sizes" in extra_metadata:
                    canvas_pos_elem.set("split_view_sizes", ",".join(str(s) for s in extra_metadata["split_view_sizes"]))
                if "patchbay_containers" in extra_metadata and extra_metadata["patchbay_containers"]:
                    c_elem = ET.SubElement(canvas_pos_elem, "Containers")
                    c_elem.text = json.dumps(extra_metadata["patchbay_containers"])

            for pos_data in positions:
                name = str(pos_data.get("name", "")).strip()
                if not name:
                    continue
                p_elem = ET.SubElement(canvas_pos_elem, "Position")
                p_elem.set("name", name)
                p_elem.set("pos1x", str(int(round(pos_data.get("pos1x", 0)))))
                p_elem.set("pos1y", str(int(round(pos_data.get("pos1y", 0)))))
                p_elem.set("pos2x", str(int(round(pos_data.get("pos2x", 0)))))
                p_elem.set("pos2y", str(int(round(pos_data.get("pos2y", 0)))))
                p_elem.set("split", "1" if pos_data.get("split") else "0")
                if pos_data.get("color"):
                    p_elem.set("color", str(pos_data["color"]))
                if pos_data.get("hide_unconnected_ports"):
                    p_elem.set("hide_unconnected_ports", "1")

            _atomic_write_xml(tree, filepath)
            return True
        except Exception as e:
            print("CarlaXmlProjectHandler::save_positions error:", e)
            return False

    def load_full_project_as_xml_path(self, filepath, force_bridged=False):
        if not force_bridged:
            return filepath
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag == "CARLA-PROJECT":
                eng_settings = root.find("EngineSettings")
                if eng_settings is None:
                    eng_settings = ET.SubElement(root, "EngineSettings")
                pref = eng_settings.find("PreferPluginBridges")
                if pref is None:
                    pref = ET.SubElement(eng_settings, "PreferPluginBridges")
                pref.text = "true"
                tmp_xml = _temp_project_path()
                tree.write(tmp_xml, encoding="UTF-8", xml_declaration=True)
                return tmp_xml
        except Exception as e:
            print("CarlaXmlProjectHandler::load_full_project_as_xml_path force_bridged error:", e)
        return filepath

    def save_full_project_from_xml_path(self, target_filepath, source_xml_path):
        if target_filepath != source_xml_path:
            import shutil
            tmp_path = target_filepath + ".tmp"
            shutil.copy2(source_xml_path, tmp_path)
            os.replace(tmp_path, target_filepath)
        return True


class CarlaJsonProjectHandler(BaseProjectHandler):
    """Handler for modern Carla JSON projects (.carjp, .json) with full validation"""
    def can_handle(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return False
        if filepath.lower().endswith((".carjp", ".json")):
            return True
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(128).strip()
                return head.startswith("{") and ("carla" in head.lower() or "canvas_positions" in head.lower())
        except Exception:
            return False

    def _read_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if not isinstance(doc, dict):
            raise ProjectFormatError("Invalid JSON root: expected object")
        return doc

    def load_root(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            doc = self._read_json(filepath)
        except Exception:
            return None
        if "CARLA-PROJECT" not in doc or not isinstance(doc["CARLA-PROJECT"], dict):
            return None
        try:
            return dict_to_xml_elem("CARLA-PROJECT", doc["CARLA-PROJECT"])
        except Exception:
            return None

    def load_positions(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return []
        try:
            doc = self._read_json(filepath)
            positions = CanvasPositionList()
            is_infinite = False
            split_view_enabled = None
            split_view_sizes = None
            containers_data = doc.get("patchbay_containers")
            if "CARLA-PROJECT" in doc and isinstance(doc["CARLA-PROJECT"], dict):
                c_pos = doc["CARLA-PROJECT"].get("CanvasPositions", {})
                if isinstance(c_pos, dict):
                    attrs = c_pos.get("@attributes", {})
                    is_infinite = str(attrs.get("infinite_canvas", "false")).lower() in ("1", "true")
                    if "split_view_enabled" in attrs:
                        split_view_enabled = str(attrs.get("split_view_enabled", "0")).lower() in ("1", "true")
                    if "split_view_sizes" in attrs:
                        try:
                            split_view_sizes = [int(s) for s in str(attrs.get("split_view_sizes", "")).split(",") if s.strip()]
                        except Exception:
                            pass
                    if "Containers" in c_pos:
                        try:
                            containers_data = c_pos["Containers"] if isinstance(c_pos["Containers"], list) else json.loads(str(c_pos["Containers"]))
                        except Exception:
                            pass
                    pos_entries = c_pos.get("Position", [])
                    if isinstance(pos_entries, dict):
                        pos_entries = [pos_entries]
                    for pe in pos_entries:
                        attrs_pe = pe.get("@attributes", pe)
                        if "name" in attrs_pe:
                            positions.append({
                                "name": str(attrs_pe["name"]),
                                "pos1x": float(attrs_pe.get("pos1x", 0)),
                                "pos1y": float(attrs_pe.get("pos1y", 0)),
                                "pos2x": float(attrs_pe.get("pos2x", 0)),
                                "pos2y": float(attrs_pe.get("pos2y", 0)),
                                "split": str(attrs_pe.get("split", "0")) in ("1", "true", "True"),
                                "color": str(attrs_pe.get("color", "")),
                                "hide_unconnected_ports": str(attrs_pe.get("hide_unconnected_ports", "0")) in ("1", "true", "True"),
                            })

            if not positions:
                is_infinite = bool(doc.get("infinite_canvas", False))
                if "split_view_enabled" in doc:
                    split_view_enabled = bool(doc.get("split_view_enabled"))
                if "split_view_sizes" in doc:
                    split_view_sizes = doc.get("split_view_sizes")
                raw_positions = doc.get("canvas_positions", doc.get("positions", []))
                for p in raw_positions:
                    if isinstance(p, dict) and "name" in p:
                        positions.append({
                            "name": str(p["name"]),
                            "pos1x": float(p.get("pos1x", 0)),
                            "pos1y": float(p.get("pos1y", 0)),
                            "pos2x": float(p.get("pos2x", 0)),
                            "pos2y": float(p.get("pos2y", 0)),
                            "split": bool(p.get("split", False)),
                            "color": str(p.get("color", "")),
                            "hide_unconnected_ports": bool(p.get("hide_unconnected_ports", False)),
                        })

            setattr(positions, "infinite_canvas", is_infinite)
            if split_view_enabled is not None:
                setattr(positions, "split_view_enabled", split_view_enabled)
            if split_view_sizes is not None:
                setattr(positions, "split_view_sizes", split_view_sizes)
            if containers_data is not None:
                setattr(positions, "patchbay_containers", containers_data)
            return positions
        except Exception as e:
            print("CarlaJsonProjectHandler::load_positions error:", e)
            return CanvasPositionList()

    def save_positions(self, filepath, positions, extra_metadata=None):
        try:
            doc = {}
            if os.path.exists(filepath):
                try:
                    doc = self._read_json(filepath)
                except Exception:
                    doc = {}

            if "CARLA-PROJECT" in doc and isinstance(doc["CARLA-PROJECT"], dict):
                c_attrs = {"infinite_canvas": "true"}
                if extra_metadata:
                    if "split_view_enabled" in extra_metadata:
                        c_attrs["split_view_enabled"] = "1" if extra_metadata["split_view_enabled"] else "0"
                    if "split_view_sizes" in extra_metadata:
                        c_attrs["split_view_sizes"] = ",".join(str(s) for s in extra_metadata["split_view_sizes"])

                canvas_pos_elem = {"@attributes": c_attrs, "Position": []}
                if extra_metadata and "patchbay_containers" in extra_metadata and extra_metadata["patchbay_containers"]:
                    canvas_pos_elem["Containers"] = extra_metadata["patchbay_containers"]
                    doc["patchbay_containers"] = extra_metadata["patchbay_containers"]
                for p in positions:
                    name = str(p.get("name", "")).strip()
                    if not name:
                        continue
                    attrs = {
                        "name": name,
                        "pos1x": str(int(round(p.get("pos1x", 0)))),
                        "pos1y": str(int(round(p.get("pos1y", 0)))),
                        "pos2x": str(int(round(p.get("pos2x", 0)))),
                        "pos2y": str(int(round(p.get("pos2y", 0)))),
                        "split": "1" if p.get("split") else "0",
                    }
                    if p.get("color"):
                        attrs["color"] = str(p["color"])
                    if p.get("hide_unconnected_ports"):
                        attrs["hide_unconnected_ports"] = "1"
                    canvas_pos_elem["Position"].append({"@attributes": attrs})
                doc["CARLA-PROJECT"]["CanvasPositions"] = canvas_pos_elem
            else:
                doc["format"] = "carla-project-json"
                doc["version"] = "1.0"
                doc["infinite_canvas"] = True
                if extra_metadata:
                    doc["split_view_enabled"] = bool(extra_metadata.get("split_view_enabled", False))
                    if "split_view_sizes" in extra_metadata:
                        doc["split_view_sizes"] = extra_metadata["split_view_sizes"]
                    if "patchbay_containers" in extra_metadata:
                        doc["patchbay_containers"] = extra_metadata["patchbay_containers"]

                clean_positions = []
                for p in positions:
                    name = str(p.get("name", "")).strip()
                    if not name:
                        continue
                    entry = {
                        "name": name,
                        "pos1x": int(round(p.get("pos1x", 0))),
                        "pos1y": int(round(p.get("pos1y", 0))),
                        "pos2x": int(round(p.get("pos2x", 0))),
                        "pos2y": int(round(p.get("pos2y", 0))),
                        "split": bool(p.get("split", False)),
                    }
                    if p.get("color"):
                        entry["color"] = str(p["color"])
                    if p.get("hide_unconnected_ports"):
                        entry["hide_unconnected_ports"] = True
                    clean_positions.append(entry)
                doc["canvas_positions"] = clean_positions

            tmp_path = filepath + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent="\t")
            os.replace(tmp_path, filepath)
            return True
        except Exception as e:
            print("CarlaJsonProjectHandler::save_positions error:", e)
            return False

    def load_full_project_as_xml_path(self, filepath, force_bridged=False):
        """Converts full JSON project (.carjp) into an XML ElementTree file for Carla backend loading."""
        doc = self._read_json(filepath)
        if "CARLA-PROJECT" not in doc:
            raise ProjectFormatError("Missing CARLA-PROJECT root key in JSON project")

        project_dict = dict(doc["CARLA-PROJECT"])
        if force_bridged:
            eng_settings = dict(project_dict.get("EngineSettings", {}))
            eng_settings["PreferPluginBridges"] = "true"
            project_dict["EngineSettings"] = eng_settings

        root = dict_to_xml_elem("CARLA-PROJECT", project_dict)
        tree = ET.ElementTree(root)

        tmp_xml_path = _temp_project_path()
        tree.write(tmp_xml_path, encoding="UTF-8", xml_declaration=True)
        return tmp_xml_path

    def save_full_project_from_xml_path(self, target_filepath, source_xml_path):
        """Converts saved XML project from Carla backend into validated .carjp JSON format."""
        tree = ET.parse(source_xml_path)
        root = tree.getroot()
        if root.tag != "CARLA-PROJECT":
            raise ProjectFormatError("Source is not a valid CARLA-PROJECT XML")

        doc = {
            "format": "carla-project-json",
            "version": "1.0",
            "CARLA-PROJECT": xml_elem_to_dict(root)
        }

        tmp_target = target_filepath + ".tmp"
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent="\t")
        os.replace(tmp_target, target_filepath)
        return True


class ProjectFormat:
    """
    A single file type, owned entirely by the save manager.

    The rest of the program only ever carries a *tag* (the format id: "xml", "json", "state")
    plus a filename. Extensions are resolved here and nowhere else.
    """
    def __init__(self, id, ext, display, kind="project", alt_exts=(), handler=None, filter_exts=None, saveable=True):
        self.id = id
        self.ext = ext
        self.display = display
        self.kind = kind
        self.alt_exts = tuple(alt_exts)
        self.handler = handler
        # the C++ engine only reads and writes CARLA-PROJECT XML, so every other format costs a
        # full convert on save; formats with saveable=False stay readable but are not offered
        self.saveable = saveable
        # legacy aliases are accepted when loading, but stay out of file-dialog filters so that
        # every unrelated *.json on disk does not show up in the open/save picker
        self.filter_exts = tuple(alt_exts) if filter_exts is None else tuple(filter_exts)
        self.patterns = ("*" + ext,) + tuple("*" + e for e in self.filter_exts if e != ext)

    @property
    def extensions(self):
        return (self.ext,) + self.alt_exts

    def has_primary_extension(self, filepath):
        if not filepath:
            return False
        return str(filepath).lower().endswith(self.ext)

    def has_extension(self, filepath):
        if not filepath:
            return False
        path = str(filepath).lower()
        return any(path.endswith(ext) for ext in self.extensions)

    def __repr__(self):
        return "ProjectFormat(%r, %r, kind=%r)" % (self.id, self.ext, self.kind)


class ProjectStorageManager:
    """Dispatches and coordinates project file persistence across formats"""

    def __init__(self):
        self._formats = [
            ProjectFormat("xml", ".carxp", "Carla XML Project", "project",
                          handler=CarlaXmlProjectHandler()),
            ProjectFormat("json", ".carjp", "Carla JSON Project", "project",
                          alt_exts=(".json",), filter_exts=(), handler=CarlaJsonProjectHandler(),
                          saveable=False),
            ProjectFormat("state", ".carxs", "Carla State File", "state"),
        ]
        self._defaults = {"project": "xml", "state": "state"}

    # ------------------------------------------------------------------------------------------------
    # registry

    def formats(self, kind=None):
        if kind is None:
            return list(self._formats)
        return [f for f in self._formats if f.kind == kind]

    def get_format_by_tag(self, tag):
        if not tag:
            return None
        for fmt in self._formats:
            if fmt.id == tag:
                return fmt
        return None

    def default_format(self, kind="project"):
        fmt = self.get_format_by_tag(self._defaults.get(kind))
        if fmt is not None:
            return fmt
        matching = self.formats(kind)
        if not matching:
            raise KeyError("unknown format kind: %s" % (kind,))
        return matching[0]

    def default_extension(self, kind="project"):
        return self.default_format(kind).ext

    def extensions(self, kind="project"):
        exts = []
        for fmt in self.formats(kind):
            for ext in fmt.extensions:
                if ext not in exts:
                    exts.append(ext)
        return exts

    # ------------------------------------------------------------------------------------------------
    # resolution (never raises, never leaks extensions upwards)

    def get_format(self, filepath):
        """Resolves a filename to its format using its extension, falling back to content sniffing."""
        if not filepath:
            return None
        for fmt in self._formats:
            if fmt.handler is None:
                continue
            if fmt.has_extension(filepath) or fmt.handler.can_handle(filepath):
                return fmt
        for fmt in self._formats:
            if fmt.has_extension(filepath):
                return fmt
        return None

    def get_format_tag(self, filepath):
        fmt = self.get_format(filepath)
        return fmt.id if fmt is not None else None

    def is_project_file(self, filepath):
        """
        True when the program should treat *filepath* as a loadable project.

        Primary extensions are trusted as-is. Legacy aliases (.json) and extension-less files are
        only accepted once their content proves to be a Carla project, so unrelated files are
        never mistaken for sessions.
        """
        if not filepath:
            return False
        for fmt in self._formats:
            if fmt.kind == "project" and fmt.has_primary_extension(filepath):
                return True
        return self.get_project_root(filepath) is not None

    def is_state_file(self, filepath):
        if not filepath:
            return False
        for fmt in self._formats:
            if fmt.kind == "state" and fmt.has_primary_extension(filepath):
                return True
        return False

    def tag_from_filter(self, selected_filter, kind="project"):
        """Maps a QFileDialog filter string to a format tag using its (untranslated) pattern."""
        if not selected_filter:
            return None
        selected = str(selected_filter)
        for fmt in self.formats(kind):
            if fmt.ext in selected:
                return fmt.id
        return None

    def ensure_extension(self, filepath, tag=None, kind="project"):
        """Appends the chosen format's extension when the filename carries no known one."""
        if not filepath:
            return filepath
        for fmt in self.formats(kind):
            if fmt.has_extension(filepath):
                return filepath
        fmt = self.get_format_by_tag(tag)
        if fmt is None or fmt.kind != kind:
            fmt = self.default_format(kind)
        return filepath + fmt.ext

    # ------------------------------------------------------------------------------------------------
    # dialog filters

    def open_filter(self):
        projects = self.formats("project")
        all_patterns = " ".join(p for fmt in projects for p in fmt.patterns)
        parts = ["Carla Project Files (%s)" % all_patterns]
        parts += ["%s (%s)" % (fmt.display, " ".join(fmt.patterns)) for fmt in projects]
        parts += ["%s (%s)" % (fmt.display, " ".join(fmt.patterns)) for fmt in self.formats("state")]
        return ";;".join(parts)

    def save_filter(self, kind="project"):
        return ";;".join(
            "%s (%s)" % (fmt.display, " ".join(fmt.patterns))
            for fmt in self.formats(kind) if fmt.saveable
        )

    # ------------------------------------------------------------------------------------------------
    # format-agnostic I/O

    def get_project_root(self, filepath):
        """ElementTree root for any project format, or None. Callers never inspect extensions."""
        fmt = self.get_format(filepath)
        if fmt is None or fmt.handler is None:
            return None
        try:
            return fmt.handler.load_root(filepath)
        except Exception:
            return None

    def sidecar_positions_path(self, filepath):
        """
        Path of the legacy sidecar canvas-positions file for a project, or None.

        Only old-style XML projects (`.carxp` declaring VERSION 2.0) keep positions in a sidecar;
        modern formats store them inline. The format and the legacy marker are both decided here so
        callers never need to know about extensions.
        """
        fmt = self.get_format(filepath)
        if fmt is None or fmt.kind != "project" or fmt.id != "xml":
            return None
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                head = "".join(fh.readlines(90))
        except Exception:
            return None
        if head.find("<CARLA-PROJECT VERSION='2.0'>") < 0:
            return None
        base, _ext = os.path.splitext(filepath)
        return base + ".json"

    def has_sidecar_positions(self, filepath):
        sidecar = self.sidecar_positions_path(filepath)
        return bool(sidecar and os.path.exists(sidecar))

    def handler_for(self, filepath):
        fmt = self.get_format(filepath)
        if fmt is not None and fmt.handler is not None:
            return fmt.handler
        return self.default_format("project").handler

    # ------------------------------------------------------------------------------------------------
    # persistence

    def load_canvas_positions(self, filepath):
        return self.handler_for(filepath).load_positions(filepath)

    def save_canvas_positions(self, filepath, positions, extra_metadata=None):
        return self.handler_for(filepath).save_positions(filepath, positions, extra_metadata=extra_metadata)

    def prepare_for_backend_load(self, filepath, force_bridged=False):
        """Prepares a file path readable by the C++ engine (converts non-XML projects to a temp XML)."""
        return self.handler_for(filepath).load_full_project_as_xml_path(filepath, force_bridged=force_bridged)

    def prepare_for_backend_save(self, target_filepath):
        """Returns (backend_save_target, is_temporary) for saving from C++ backend."""
        fmt = self.get_format(target_filepath)
        if fmt is not None and fmt.id == "json":
            tmp_xml = target_filepath + "._tmp_carla_save.carxp"
            return tmp_xml, True
        return target_filepath, False

    def finalize_from_backend_save(self, target_filepath, backend_saved_filepath, positions=None, extra_metadata=None):
        """Finalizes backend save into target format and writes canvas positions.

        Returns False when any step failed, so callers never treat a failed save as done.
        """
        handler = self.handler_for(target_filepath)
        ok = True
        try:
            if handler.save_full_project_from_xml_path(target_filepath, backend_saved_filepath) is False:
                ok = False
            elif positions is not None and handler.save_positions(target_filepath, positions, extra_metadata=extra_metadata) is False:
                ok = False
        except Exception as e:
            print("ProjectStorageManager::finalize_from_backend_save error:", e)
            ok = False
        if backend_saved_filepath != target_filepath and os.path.exists(backend_saved_filepath):
            try:
                os.remove(backend_saved_filepath)
            except Exception:
                pass
        return ok

storage_manager = ProjectStorageManager()
