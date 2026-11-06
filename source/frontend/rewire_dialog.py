#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Rewire dialog shown when replacing a plugin in place.

from qt_compat import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
)

from rewire import (
    KIND_AUDIO,
    KIND_CV,
    KIND_MIDI,
    KIND_OTHER,
    KIND_PARAM,
    MODE_IN,
    MODE_OUT,
    is_compatible,
    match_ports,
    role_target,
    validate_rows,
)

_GROUP_LABELS = {
    (MODE_IN, KIND_AUDIO): "Audio In",
    (MODE_IN, KIND_MIDI): "Event In",
    (MODE_IN, KIND_CV): "CV In",
    (MODE_IN, KIND_PARAM): "Parameter In",
    (MODE_IN, KIND_OTHER): "Other In",
    (MODE_OUT, KIND_AUDIO): "Audio Out",
    (MODE_OUT, KIND_MIDI): "Event Out",
    (MODE_OUT, KIND_CV): "CV Out",
    (MODE_OUT, KIND_PARAM): "Parameter Out",
    (MODE_OUT, KIND_OTHER): "Other Out",
}

_REASON_LABELS = {
    "name": "name",
    "channel": "channel",
    "event": "event",
    "role": "role",
    "none": "unmatched",
}


def _target_key(target):
    if not target:
        return None
    if "role" in target:
        return ("role",) + tuple(target["role"])
    return ("port", target.get("mode"), target.get("kind"), target.get("name", "").casefold())


class RewireDialog(QDialog):
    def __init__(self, parent, old_name, new_name, rows, cable_counts, targets, exact):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Replace %s with %s") % (old_name, new_name))
        self.setMinimumSize(680, 480)
        self._old_name = old_name
        self._new_name = new_name
        self._targets = list(targets)
        self._cable_counts = dict(cable_counts or {})
        self._exact = bool(exact)
        self._base_rows = [dict(row) for row in rows]
        self._rows = []
        self._combos = []
        self._group_items = []

        outer = QVBoxLayout(self)
        outer.setSpacing(8)
        outer.setContentsMargins(12, 12, 12, 12)

        mode_text = "exact ports (instance reused)" if exact else "roles (resolved after load)"
        header = QLabel(
            self.tr("<b>%s</b> will take the place of <b>%s</b>.<br>"
                    "Matching uses %s. Unmatched cables are dropped.") % (new_name, old_name, mode_text)
        )
        header.setWordWrap(True)
        outer.addWidget(header)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Old port", "Cables", "Match", "New port"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        no_edit = getattr(QAbstractItemView, "NoEditTriggers", None)
        if no_edit is None:
            no_edit = QAbstractItemView.EditTrigger.NoEditTriggers
        self.table.setEditTriggers(no_edit)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        outer.addWidget(self.table, 1)

        controls = QHBoxLayout()
        auto_btn = QPushButton(self.tr("Auto-match"), self)
        auto_btn.clicked.connect(self._auto_match)
        controls.addWidget(auto_btn)
        controls.addStretch()
        self.summary = QLabel(self)
        controls.addWidget(self.summary)
        outer.addLayout(controls)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton(self.tr("Cancel"), self)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        self.apply_btn = QPushButton(self.tr("Replace"), self)
        self.apply_btn.setDefault(True)
        self.apply_btn.clicked.connect(self._accept_if_valid)
        buttons.addWidget(self.apply_btn)
        outer.addLayout(buttons)

        self._build_table()

    # ------------------------------------------------------------------

    def _build_table(self):
        self.table.setRowCount(0)
        self._combos = []
        self._group_items = []
        self._rows = []
        last_group = None
        for row in self._base_rows:
            old = row["old"]
            group = (old["mode"], old["kind"])
            if group != last_group:
                self._add_group_row(group)
                last_group = group
            self._add_port_row(row)
        self._update_summary()

    def _add_group_row(self, group):
        row_index = self.table.rowCount()
        self.table.insertRow(row_index)
        item = QTableWidgetItem(_GROUP_LABELS.get(group, "Ports"))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.table.setItem(row_index, 0, item)
        self.table.setSpan(row_index, 0, 1, 4)
        self._group_items.append(row_index)

    def _add_port_row(self, row):
        old = row["old"]
        row_index = self.table.rowCount()
        self.table.insertRow(row_index)

        name_item = QTableWidgetItem(old["name"] or _GROUP_LABELS.get((old["mode"], old["kind"]), old["kind"]))
        name_item.setToolTip("%s · %s" % (old["name"], _GROUP_LABELS.get((old["mode"], old["kind"]), "")))
        self.table.setItem(row_index, 0, name_item)

        cable_count = self._cable_counts.get(old["key"], 0)
        cable_item = QTableWidgetItem(str(cable_count) if cable_count else "-")
        cable_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_index, 1, cable_item)

        combo = QComboBox(self)
        combo.setMinimumWidth(200)
        combo.addItem(self.tr("Do not connect"), None)
        for target in self._targets:
            if not is_compatible(old, target):
                continue
            combo.addItem(target.get("label", "?"), target)
        matched = row.get("target")
        if matched:
            key = _target_key(matched)
            for index in range(1, combo.count()):
                if _target_key(combo.itemData(index)) == key:
                    combo.setCurrentIndex(index)
                    break
        combo.currentIndexChanged.connect(self._update_summary)
        self.table.setCellWidget(row_index, 3, combo)
        self._combos.append((row_index, old, combo, row.get("reason", "")))

        reason_item = QTableWidgetItem(_REASON_LABELS.get(row.get("reason", ""), row.get("reason", "")))
        self.table.setItem(row_index, 2, reason_item)

        self._rows.append({"old": old, "combo": combo, "reason": row.get("reason", "")})

    def _auto_match(self):
        fresh = match_ports([row["old"] for row in self._base_rows],
                            None if not self._exact else self._targets_as_ports())
        self._base_rows = fresh
        self._build_table()

    def _targets_as_ports(self):
        ports = []
        for target in self._targets:
            if "role" in target:
                continue
            ports.append({
                "key": (target.get("mode"), target.get("kind"), target.get("name")),
                "name": target.get("name", ""),
                "mode": target.get("mode", MODE_IN),
                "kind": target.get("kind", KIND_OTHER),
                "index": target.get("index", 0),
            })
        return ports

    def _update_summary(self):
        rows = self.selected_plan()
        kept = sum(1 for row in rows if row.get("target"))
        cables = 0
        dropped_cables = 0
        for row in rows:
            count = self._cable_counts.get(row["old"]["key"], 0)
            if row.get("target"):
                cables += count
            else:
                dropped_cables += count
        error = validate_rows(rows)
        self.summary.setText(
            self.tr("Kept %i/%i ports · %i cables preserved · %i dropped") % (
                kept, len(rows), cables, dropped_cables)
        )
        if error:
            self.summary.setText(self.summary.text() + "  ·  ⚠ " + error)
        self.apply_btn.setEnabled(error is None)

    def _accept_if_valid(self):
        if validate_rows(self.selected_plan()) is not None:
            return
        self.accept()

    def selected_plan(self):
        plan = []
        for entry in self._rows:
            target = entry["combo"].currentData()
            plan.append({"old": entry["old"], "target": target, "reason": entry["reason"]})
        return plan
