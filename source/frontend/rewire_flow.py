#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Replace + rewire flow, split out of carla_host.py.
# HostWindow inherits this mixin; the methods still use self for host state.

import os
import time

from qt_compat import QMessageBox, QTimer

from patchcanvas import patchcanvas
from carla_backend import PLUGIN_OPTIONS_NULL
from carla_shared import CustomMessageBox, log_carla


class RewireFlowMixin:
    def _groupForPlugin(self, pluginId):
        group = patchcanvas.canvas.group_plugin_map.get(pluginId)
        if group is not None:
            return group
        for group in patchcanvas.canvas.group_list:
            if group.plugin_id == pluginId:
                return group
        return None

    def _groupPorts(self, groupId):
        return [
            port for port in patchcanvas.canvas.port_list
            if port.group_id == groupId and getattr(port, "widget", None) is not None
        ]

    def _oldPortConnections(self, groupId):
        connections = []
        for conn in patchcanvas.canvas.connection_list:
            if conn.group_out_id == groupId or conn.group_in_id == groupId:
                connections.append(
                    (conn.group_out_id, conn.port_out_id, conn.group_in_id, conn.port_in_id)
                )
        return connections

    def _portCableCount(self, groupId, portId):
        count = 0
        for conn in patchcanvas.canvas.connection_list:
            if conn.group_out_id == groupId and conn.port_out_id == portId:
                count += 1
            elif conn.group_in_id == groupId and conn.port_in_id == portId:
                count += 1
        return count

    def _findExistingPluginPorts(self, ptype, filename, label, uniqueId, excludeId):
        """Use a live instance's ports for an exact preview, when one exists."""
        for index, pitem in enumerate(self.fPluginList):
            if pitem is None or index == excludeId:
                continue
            try:
                info = self.host.get_plugin_info(index)
            except Exception:
                continue
            if not info or info.get("type") != ptype:
                continue
            same = False
            if uniqueId and info.get("uniqueId") == uniqueId:
                same = True
            elif filename and info.get("filename") == filename:
                same = not label or info.get("label") == label
            elif label and info.get("label") == label:
                same = True
            if not same:
                continue
            group = self._groupForPlugin(index)
            if group is None:
                continue
            ports = self._groupPorts(group.group_id)
            if ports:
                return ports
        return None

    def _buildRewirePlan(self, pluginId, with_plugin_id=None):
        from rewire import actual_target, attach_catalog_roles, index_ports, match_ports, normalize_port, role_target

        if not self.host.is_engine_running() or getattr(self, "fIsProjectLoading", False):
            return None
        old_group = self._groupForPlugin(pluginId)
        if old_group is None:
            return None
        try:
            old_info = self.host.get_plugin_info(pluginId)
        except Exception:
            old_info = None
        old_label = old_info.get("label") if old_info else None
        old_ports = index_ports([normalize_port(port) for port in self._groupPorts(old_group.group_id)])
        attach_catalog_roles(old_ports, old_label)
        if not old_ports:
            return None

        new_ports = None
        new_label = None
        if with_plugin_id is not None:
            try:
                info = self.host.get_plugin_info(with_plugin_id)
            except Exception:
                info = None
            if not info:
                return None
            group = self._groupForPlugin(with_plugin_id)
            if group is None:
                return None
            new_label = info.get("label")
            new_display = info.get("name") or new_label
            new_ports = index_ports([normalize_port(port) for port in self._groupPorts(group.group_id)])
            attach_catalog_roles(new_ports, new_label)
            from carla_backend import BINARY_NATIVE
            data = (
                info.get("build") or BINARY_NATIVE, info.get("type"), info.get("filename"),
                info.get("label"), info.get("uniqueId"), None,
            )
        else:
            self._replaceTargetId = pluginId
            self._replaceRequestInfo = None
            try:
                data = self.showAddPluginDialog()
            finally:
                self._replaceTargetId = None
            if data is None:
                info = self._replaceRequestInfo
                self._replaceRequestInfo = None
                if info is None:
                    return None
                data = (
                    info.get("build"), info.get("type"), info.get("filename"),
                    info.get("label"), info.get("uniqueId"), None,
                )
            btype, ptype, filename, label, uniqueId, _extra = data
            new_label = label
            _captured = locals().get("info")
            new_display = (_captured.get("name") if isinstance(_captured, dict) else None) or label
            candidate = self._findExistingPluginPorts(ptype, filename, label, uniqueId, pluginId)
            if candidate is not None:
                new_ports = index_ports([normalize_port(port) for port in candidate])
                attach_catalog_roles(new_ports, new_label)

        btype, ptype, filename, label, uniqueId, extraPtr = data
        if new_ports is not None and not any(port["kind"] in ("audio", "midi", "cv") for port in new_ports):
            log_carla("rewire: replacement has no audio/MIDI/CV ports", level="warn")
            return None
        exact = new_ports is not None
        if exact:
            targets = []
            seen = set()
            for port in new_ports:
                target = actual_target(port)
                key = (target["mode"], target["kind"], target["name"].casefold(), target["index"])
                if key not in seen:
                    seen.add(key)
                    targets.append(target)
        else:
            targets = []
            seen = set()
            for port in old_ports:
                target = role_target(port)
                key = (target["role"], target.get("role_key"))
                if key not in seen:
                    seen.add(key)
                    targets.append(target)

        from carla_backend import PLUGIN_HAS_CUSTOM_UI, PLUGIN_OPTION_USE_BRIDGE
        hints = int((locals().get("info") or {}).get("hints", 0) or 0)
        ident = ((label or "") + " " + (filename or "")).lower()
        if (hints & PLUGIN_HAS_CUSTOM_UI) or "cardinal" in ident or "decentsampler" in ident:
            bridge_options = PLUGIN_OPTION_USE_BRIDGE
        else:
            bridge_options = 0

        log_carla(
            f"rewire: old_label={old_label!r} new_label={new_label!r} "
            f"catalog_old={bool(old_ports and old_ports[0].get('catalog_role'))} "
            f"catalog_new={bool(new_ports and new_ports[0].get('catalog_role'))}",
            level="debug",
        )
        return {
            "old_group": old_group,
            "old_ports": old_ports,
            "rows": match_ports(old_ports, new_ports if exact else None),
            "cable_counts": {
                port["key"]: self._portCableCount(old_group.group_id, port["key"])
                for port in old_ports
            },
            "targets": targets,
            "exact": exact,
            "options": bridge_options,
            "data": (btype, ptype, filename, label, uniqueId, extraPtr),
            "label": new_display or os.path.basename(filename or "") or "plugin",
        }

    def showReplaceWithRewire(self, pluginId, auto=False, with_plugin_id=None, dry_run=False):
        from rewire import validate_rows
        from rewire_dialog import RewireDialog

        plan_info = self._buildRewirePlan(pluginId, with_plugin_id=with_plugin_id)
        if plan_info is None:
            return {"ok": False, "error": "cannot build a rewire plan for this plugin"}

        rows = plan_info["rows"]
        cable_counts = plan_info["cable_counts"]

        if dry_run:
            kept = sum(1 for row in rows if row.get("target"))
            cables_kept = sum(cable_counts.get(row["old"]["key"], 0) for row in rows if row.get("target"))
            cables_dropped = sum(cable_counts.get(row["old"]["key"], 0) for row in rows if not row.get("target"))
            return {
                "ok": True, "dry_run": True, "exact": plan_info["exact"],
                "kept": kept, "ports": len(rows),
                "cables_kept": cables_kept, "cables_dropped": cables_dropped,
                "rows": [
                    {
                        "old": row["old"]["name"],
                        "target": (row.get("target") or {}).get("label"),
                        "reason": row.get("reason"),
                    }
                    for row in rows
                ],
            }

        if not auto:
            dialog = RewireDialog(
                self, plan_info["old_group"].group_name, plan_info["label"],
                rows, cable_counts, plan_info["targets"], plan_info["exact"],
            )
            if not dialog.exec_():
                return {"ok": False, "cancelled": True}
            rows = dialog.selected_plan()

        error = validate_rows(rows)
        if error is not None:
            return {"ok": False, "error": error}
        return self._applyRewire(plan_info, rows)

    def _applyRewire(self, plan_info, rows):
        old_group = plan_info["old_group"]
        pluginId = old_group.plugin_id
        btype, ptype, filename, label, uniqueId, extraPtr = plan_info["data"]

        old_connections = self._oldPortConnections(old_group.group_id)
        old_gid = old_group.group_id
        try:
            pos = old_group.widgets[0].pos()
        except Exception:
            pos = None

        self._rewireResult = {"done": False, "plugin": pluginId, "label": plan_info["label"]}

        if not self.host.replace_plugin(pluginId):
            self._rewireResult = {"done": True, "error": "replace failed", "plugin": pluginId}
            CustomMessageBox(
                self, QMessageBox.Critical, self.tr("Error"), self.tr("Failed to replace plugin"),
                self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok,
            )
            return {"ok": False, "error": self.host.get_last_error()}

        if pos is not None:
            patchcanvas.setInitialPos(pos.x(), pos.y())

        try:
            ok = self.host.add_plugin(
                btype, ptype, filename, None, label, uniqueId, extraPtr,
                plan_info.get("options", PLUGIN_OPTIONS_NULL)
            )
        except Exception as exc:
            log_carla("rewire: add_plugin raised: %s" % exc, level="warn")
            ok = False
        if not ok:
            self.host.replace_plugin(self.host.get_max_plugin_number())
            if self._groupForPlugin(pluginId) is not None:
                log_carla("rewire: load failed, old plugin kept", level="warn")
            self._rewireResult = {"done": True, "error": "plugin load failed", "plugin": pluginId}
            CustomMessageBox(
                self, QMessageBox.Critical, self.tr("Error"), self.tr("Failed to load plugin"),
                self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok,
            )
            return {"ok": False, "error": self.host.get_last_error()}

        if pluginId in (getattr(self, "fNoBridgePlugins", None) or []):
            # The slot changed plugin; let the new one follow the normal UI policy.
            self.fNoBridgePlugins.remove(pluginId)
        self._rewireState = {
            "pluginId": pluginId,
            "old_gid": old_gid,
            "old_name": old_group.group_name,
            "plan": rows,
            "connections": old_connections,
            "label": plan_info["label"],
            "deadline": time.monotonic() + 60.0,
            "started": time.monotonic(),
            "last_count": -1,
            "adopted": False,
        }
        QTimer.singleShot(200, self._pollRewire)
        return {"ok": True, "started": True, "plugin": pluginId}

    def _adoptRewiredNode(self, old_gid, new_group):
        """The engine creates a new patchbay client on replace; carry the old node's
        placement/color over and remove the empty old group."""
        old_group = next((g for g in patchcanvas.canvas.group_list if g.group_id == old_gid), None)
        if old_group is None or new_group is None or new_group.group_id == old_gid:
            return
        old_box = old_group.widgets[0] if old_group.widgets else None
        new_box = new_group.widgets[0] if new_group.widgets else None
        if old_box is None or new_box is None:
            return
        old_sbox = old_group.widgets[1] if old_group.split and len(old_group.widgets) > 1 else None
        old_sbox_pos = old_sbox.pos() if old_sbox is not None else None
        try:
            if getattr(old_box, "m_custom_color", None):
                new_box.setCustomColor(old_box.m_custom_color.name(), notify=False)
            if getattr(old_box, "m_hide_unconnected_ports", False):
                new_box.setHideUnconnectedPorts(True)
            new_box.setPos(old_box.pos())
            for container in patchcanvas.canvas.container_list:
                if container.containsBox(old_box):
                    container.removeItem(old_box, to_standby=False)
                    container.addItem(new_box)
                    break
            if old_sbox is not None:
                if not new_group.split:
                    patchcanvas.splitGroup(new_group.group_id)
                if new_group.split and len(new_group.widgets) > 1 and new_group.widgets[1] is not None:
                    new_group.widgets[1].setPos(old_sbox_pos)
                    for container in patchcanvas.canvas.container_list:
                        if container.containsBox(old_sbox):
                            container.removeItem(old_sbox, to_standby=False)
                            container.addItem(new_group.widgets[1])
                            break
        except (RuntimeError, Exception):
            pass
        plugin_id = new_group.plugin_id
        patchcanvas.removeGroup(old_gid)
        patchcanvas.canvas.group_plugin_map[plugin_id] = new_group

    def _pollRewire(self):
        state = getattr(self, "_rewireState", None)
        if state is None:
            return
        group = self._groupForPlugin(state["pluginId"])
        if (group is not None and group.group_id != state["old_gid"]
                and not state.get("adopted")):
            # The engine creates a new client; move it into the old node's place
            # immediately instead of showing both nodes while ports arrive.
            self._adoptRewiredNode(state["old_gid"], group)
            state["adopted"] = True
        ports = self._groupPorts(group.group_id) if group is not None else []
        count = len(ports)
        now = time.monotonic()
        added_at = state.get("plugin_added_at")
        ready = added_at is not None and now - added_at >= 0.3
        if not ready and added_at is None and now - state["started"] > 2.5:
            ready = True
        if ready and count > 0 and count == state.get("last_count", -1):
            self._finishRewire(group, ports)
            return
        state["last_count"] = count
        if count == 0 and added_at is not None and now - added_at >= 3.0:
            try:
                info = self.host.get_plugin_info(state["pluginId"]) or {}
            except Exception:
                info = {}
            if not any(int(info.get(key, 0) or 0) for key in ("audioIns", "audioOuts", "midiIns", "midiOuts")):
                self._finishRewire(group, ports)
                return
        if now > state["deadline"]:
            self._finishRewire(group, ports)
            return
        QTimer.singleShot(150, self._pollRewire)

    def _dropStaleRewireGroups(self, old_gid, old_name, keep_gid):
        """Drop a leftover group for the replaced client.

        In multi-client JACK the old bridge can stay registered with no ports and
        never send a client-removed event, leaving an empty node behind.
        shortcut: hides the empty node; fix the bridge teardown if the stale client
        starts showing up in external patchbays.
        """
        stale = [
            group for group in patchcanvas.canvas.group_list
            if group.group_id not in (old_gid, keep_gid)
            and group.group_name == old_name
            and group.plugin_id < 0
            and not self._groupPorts(group.group_id)
        ]
        for group in stale:
            log_carla(
                f"rewire: dropping stale client group '{old_name}' id={group.group_id}",
                level="debug",
            )
            patchcanvas.removeGroup(group.group_id)

    def _finishRewire(self, group, new_ports):
        from rewire import attach_catalog_roles, build_rewire_connections, index_ports, normalize_port

        state = getattr(self, "_rewireState", None)
        self._rewireState = None
        if state is None or group is None:
            return

        try:
            new_info = self.host.get_plugin_info(state["pluginId"])
        except Exception:
            new_info = None
        new_ports = index_ports([normalize_port(port) for port in new_ports])
        attach_catalog_roles(new_ports, new_info.get("label") if new_info else None)
        connections, dropped = build_rewire_connections(
            state["plan"], state["old_gid"], state["connections"], new_ports, group.group_id)
        kept = failed = 0
        for args in connections:
            if self.host.patchbay_connect(self.fExternalPatchbay, *args):
                kept += 1
            else:
                failed += 1

        if group.group_id != state["old_gid"]:
            self._adoptRewiredNode(state["old_gid"], group)
        old_gid = state["old_gid"]
        old_name = state.get("old_name")
        if old_name:
            keep_gid = group.group_id
            self._dropStaleRewireGroups(old_gid, old_name, keep_gid)
            # The old bridge may unregister asynchronously; sweep once more.
            QTimer.singleShot(
                2000,
                lambda: self._dropStaleRewireGroups(old_gid, old_name, keep_gid),
            )

        try:
            patchcanvas.canvas.scene.clearSelection()
            if group.widgets and group.widgets[0] is not None:
                group.widgets[0].setSelected(True)
        except Exception:
            pass

        label = group.group_name or state["label"]
        self._rewireResult = {
            "done": True, "kept": kept, "dropped": dropped, "failed": failed,
            "label": label, "plugin": state["pluginId"],
        }
        self.markProjectModified()
        message = "Replaced with %s: kept %i cable(s), dropped %i, failed %i" % (
            label, kept, dropped, failed)
        log_carla(message)
        if hasattr(self.ui, "statusbar"):
            self.ui.statusbar.showMessage(message, 8000)
        self.updateMiniCanvasLater()

