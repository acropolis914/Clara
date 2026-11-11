#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)
# ------------------------------------------------------------------------------------------------------------
import re

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)
# ------------------------------------------------------------------------------------------------------------

from carla_backend import *
from carla_shared import *
from carla_widgets import *
from patchcanvas import patchcanvas

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)
# ------------------------------------------------------------------------------------------------------------
from canvas_helpers import _canvas_locked, _get_event_global_pos
from canvas_toolbar import CanvasToolButton
from qt_compat import (
    QAction,
    QApplication,
    QColor,
    QColorDialog,
    QCursor,
    QEvent,
    QFont,
    QFontDatabase,
    QFrame,
    QHBoxLayout,
    QIcon,
    QImage,
    QLabel,
    QLineEdit,
    QMenu,
    QMouseEvent,
    QObject,
    QPainter,
    QPainterPathStroker,
    QPixmap,
    QPoint,
    QPointF,
    QPushButton,
    QRect,
    QStyle,
    QStyleOptionButton,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------------------------------------------------------
# Stereo Autowiring and Disconnect Helpers
# ------------------------------------------------------------------------------------------------------------


class CanvasContextToolBarOverlay(QFrame):
    """Floating context-sensitive horizontal action toolbar centered on the patchbay's top edge."""

    def __init__(self, graphicsView, parent=None):
        super().__init__(parent or graphicsView.viewport())
        self.setObjectName("canvas_context_toolbar_overlay")
        self.graphicsView = graphicsView
        self._dragPos = None
        self._userMoved = False

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 3, 6, 3)
        self.layout.setSpacing(3)

        self.font_family = getBestNerdFont()
        self.font = QFont(self.font_family, 12) if self.font_family else QFont()
        if not self.font_family:
            self.font.setPointSize(10)

        # Persistent quick-search field (kept out of the rebuilt action items so
        # it survives selection changes). Rounded textbox housed in the bar.
        self.searchEdit = QLineEdit(self)
        self.searchEdit.setObjectName("canvasSearchEdit")
        self.searchEdit.setPlaceholderText("Search nodes…")
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setFixedHeight(24)
        # Shrinkable rather than fixed: when the toolbar clamps to a narrow
        # canvas viewport the field compresses instead of overflowing the bar.
        self.searchEdit.setMinimumWidth(120)
        self.searchEdit.setMaximumWidth(170)
        self.searchEdit.textChanged.connect(self._slot_search_changed)
        self.searchEdit.returnPressed.connect(self._slot_search_accept)
        self.searchEdit.installEventFilter(self)

        self.updateSelection()

    def _slot_search_changed(self, text):
        gv = self.graphicsView
        if hasattr(gv, "_onSearchTextChanged"):
            gv._onSearchTextChanged(text)

    def _slot_search_accept(self):
        gv = self.graphicsView
        if hasattr(gv, "_onSearchAccept"):
            gv._onSearchAccept()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "searchEdit", None):
            ktype = QEvent.Type.KeyPress if hasattr(QEvent, "Type") else QEvent.KeyPress
            if event.type() == ktype:
                if event.key() == Qt.Key_Escape:
                    self.searchEdit.clearFocus()
                    gv = self.graphicsView
                    if hasattr(gv, "hideSearch"):
                        gv.hideSearch()
                    return True
                if event.key() in (Qt.Key_Down, Qt.Key_Up):
                    lst = getattr(self.graphicsView, "fSearchList", None)
                    if lst is not None and lst.isVisible() and lst.count():
                        lst.setFocus()
                        lst.setCurrentRow(
                            0 if event.key() == Qt.Key_Down else lst.count() - 1
                        )
                        return True
        return QFrame.eventFilter(self, obj, event)

    def clearLayout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not getattr(self, "searchEdit", None):
                w.setParent(None)
                w.deleteLater()

    def addSeparator(self):
        line = QFrame(self)
        line.setObjectName("canvasToolbarSeparator")
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setFixedSize(1, 18)
        self.layout.addWidget(line)
        self._items.append(line)

    def addButton(self, icon, tooltip, callback, checkable=False, checked=False):
        btn = CanvasToolButton("", self)
        btn.setToolTip(tooltip)
        try:
            from widgets.lucide import bind_icon
            bind_icon(btn, icon, size=14)
        except Exception:
            btn.setText(icon)
        # Matches the QSS tile size for buttons inside the context toolbar
        btn.setFixedSize(24, 24)
        btn.ensurePolished()
        if checkable:
            btn.setCheckable(True)
            btn.setChecked(checked)
        btn.clicked.connect(callback)
        self.layout.addWidget(btn)
        self._items.append(btn)
        return btn

    def addLabel(self, text, tooltip=""):
        lbl = QLabel(text, self)
        lbl.setObjectName("canvasContextLabel")
        if tooltip:
            lbl.setToolTip(tooltip)
        self.layout.addWidget(lbl)
        self._items.append(lbl)
        return lbl

    def updateSelection(self):
        self._items = []
        self.clearLayout()
        selected = patchcanvas.getSelectedNodes()
        count = len(selected)

        # Quick-search field always leads the bar (rounded textbox)
        search = getattr(self, "searchEdit", None)
        if search is not None:
            search.show()
            self.layout.addWidget(search)
            self._items.append(search)
            self.addSeparator()

        # Icons: Lucide names (bound as recolored QIcons in addButton)
        icon_arr = "network"
        icon_repel = "move"
        icon_aside = "pin"
        icon_sel = "square-check"
        icon_desel = "x"
        icon_inv = "arrow-right-left"
        icon_edit = "sliders-horizontal"
        icon_ui = "monitor"
        icon_rack = "boxes"
        icon_clone = "copy"
        icon_ren = "pencil"
        icon_del = "trash-2"
        icon_cut = "unlink"
        icon_split = "columns-2"
        icon_color = "brush"
        icon_prop = "info"
        icon_power = "power"
        icon_bypass = "ban"
        icon_ports = "eye-off"
        icon_al_h = "align-center-horizontal"
        icon_al_v = "align-center-vertical"
        icon_dist_h = "move-horizontal"
        icon_dist_v = "move-vertical"
        icon_tools = "settings-2"

        # Check for selected containers in the scene
        selected_containers = []
        if self.graphicsView and self.graphicsView.scene():
            selected_containers = [
                it for it in self.graphicsView.scene().selectedItems()
                if it and it.type() == patchcanvas.CanvasContainerType
            ]

        if count == 0 and selected_containers:
            # Single or Multiple Container Context Actions
            c = selected_containers[0]
            c_name = getattr(c, "m_title", "Group")
            short_c_name = (c_name[:14] + "…") if len(c_name) > 15 else c_name
            self.addLabel(f"[GROUP] {short_c_name.upper()}", f"Container: {c_name}")
            self.addSeparator()

            # Rename
            self.addButton(icon_ren, "Rename Container...", c.promptRename)

            # Layout Mode switcher
            btnLayout = self.addButton(icon_split, f"Layout Mode: {getattr(c, 'm_layout_mode', 'vbox').upper()}", lambda: None)
            btnLayout.clicked.disconnect()
            btnLayout.clicked.connect(lambda: self._slot_show_container_layout_menu(btnLayout, c))

            # Color Picker
            btnCColor = self.addButton(icon_color, "Container Color...", lambda: None)
            btnCColor.clicked.disconnect()
            btnCColor.clicked.connect(lambda: self._slot_show_color_menu(btnCColor, [c]))

            # Collapse / Expand
            is_col = getattr(c, "m_collapsed", False)
            col_icon = "plus" if is_col else "minus"
            col_tip = "Expand Group" if is_col else "Collapse Group"
            self.addButton(col_icon, col_tip, lambda: (c.toggleCollapse(), self.updateSelection()))

            self.addButton(icon_tools, "Auto-Arrange Members", lambda: (c.autoArrangeMembers(), self.updateSelection()))

            # Ungroup
            self.addButton(icon_del, "Ungroup / Dissolve Container", lambda: (c.ungroup(), self.updateSelection()))
            self.addSeparator()
            self.addButton(icon_desel, "Deselect (Esc)", patchcanvas.deselectAllNodes)

        elif count == 0:
            # Global Canvas Actions
            self.addLabel("CANVAS", "Patchbay Canvas Actions")
            self.addSeparator()

            self.addButton(
                icon_aside, "Park Disconnected Nodes Aside", self._slot_move_aside_all
            )
            self.addSeparator()
            self.addButton(
                icon_sel, "Select All Nodes (Ctrl+A)", patchcanvas.selectAllNodes
            )

        elif count == 1:
            # Single Node Context Actions
            node = selected[0]
            name = getattr(node, "m_group_name", "Node")
            short_name = (name[:14] + "…") if len(name) > 15 else name

            badge = getattr(node, "m_type_badge", "")
            badge_txt = f"[{badge}] " if badge else ""
            self.addLabel(
                f"{badge_txt}{short_name.upper()}", f"{name} ({badge or 'Node'})"
            )
            self.addSeparator()

            plugin_id = getattr(node, "m_plugin_id", -1)
            has_plugin = 0 <= plugin_id <= patchcanvas.MAX_PLUGIN_ID_ALLOWED
            has_ui = getattr(node, "m_plugin_ui", False)

            if has_plugin:
                # Power & Bypass
                self.addButton(
                    icon_power,
                    "Power / Toggle Active",
                    lambda: self._slot_toggle_power(node),
                )
                self.addButton(
                    icon_bypass,
                    "Toggle Bypass (Dry/Wet)",
                    lambda: self._slot_toggle_bypass(node),
                )
                self.addSeparator()

                # Parameter Edit & Custom UI
                self.addButton(
                    icon_edit,
                    "Edit Parameters",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_EDIT, plugin_id, 0, ""
                    ),
                )
                if has_ui:
                    self.addButton(
                        icon_ui,
                        "Show Custom Plugin GUI",
                        lambda: patchcanvas.canvas.callback(
                            patchcanvas.ACTION_PLUGIN_SHOW_UI, plugin_id, 0, ""
                        ),
                    )
                self.addButton(
                    icon_rack,
                    "Jump to Plugin in Rack Tab",
                    lambda: self._slot_jump_rack(plugin_id),
                )
                self.addButton(
                    icon_clone,
                    "Duplicate / Clone Plugin",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_CLONE, plugin_id, 0, ""
                    ),
                )
                self.addButton(
                    icon_ren,
                    "Rename Plugin...",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_RENAME, plugin_id, 0, ""
                    ),
                )
                self.addButton(
                    icon_del,
                    "Remove Plugin",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_REMOVE, plugin_id, 0, ""
                    ),
                )
                self.addSeparator()

            # Appearance & Box Setup
            btnColor = self.addButton(
                icon_color, "Node Tint Color Presets & Custom...", lambda: None
            )
            btnColor.clicked.disconnect()
            btnColor.clicked.connect(
                lambda: self._slot_show_color_menu(btnColor, [node])
            )

            if hasattr(node, "showPropertiesDialog"):
                self.addButton(
                    icon_prop, "Node Properties & Badges...", node.showPropertiesDialog
                )

            # Hide/Show unconnected ports
            hiding_ports = getattr(node, "m_hide_unconnected_ports", False)
            self.addButton(
                icon_ports,
                "Toggle Hide Unconnected Ports",
                lambda: self._slot_toggle_hide_ports(node),
                checkable=True,
                checked=hiding_ports,
            )

            # Split/Join if available
            split_label = "Join" if getattr(node, "m_split", False) else "Split"
            self.addButton(
                icon_split,
                f"{split_label} Input/Output Box Groups",
                lambda: self._slot_split_join(node),
            )

            # Disconnect all cables from this node
            self.addButton(
                icon_cut,
                "Disconnect All Cables from This Node",
                lambda: self._slot_disconnect_node(node),
            )

            self.addSeparator()
            self.addButton(
                icon_arr,
                "Arrange Connected Subgraph (layers)",
                lambda: patchcanvas.arrangeConnected(node, "both"),
            )
            self.addButton(
                icon_tools,
                "Auto-Arrange Subgraph (layout algorithm)",
                lambda: patchcanvas.autoArrangeAround(node),
            )
            self.addButton(
                icon_aside,
                "Park This Node Aside",
                lambda: patchcanvas.moveAsideNonConnectedNodes(node),
            )
            self.addButton(icon_desel, "Deselect (Esc)", patchcanvas.deselectAllNodes)

        else:
            # Multiple Nodes Batch Actions
            self.addLabel(f"{count} NODES", f"{count} Selected Nodes")
            self.addSeparator()

            # Batch Align & Distribute
            self.addButton(
                icon_al_h,
                "Align Selected Nodes Horizontally",
                lambda: patchcanvas.alignSelected("horizontal"),
            )
            self.addButton(
                icon_al_v,
                "Align Selected Nodes Vertically",
                lambda: patchcanvas.alignSelected("vertical"),
            )
            self.addButton(
                icon_dist_h,
                "Distribute Horizontally with Equal Spacing",
                lambda: patchcanvas.alignSelected("distribute_h"),
            )
            self.addButton(
                icon_dist_v,
                "Distribute Vertically with Equal Spacing",
                lambda: patchcanvas.alignSelected("distribute_v"),
            )
            self.addButton(
                icon_repel,
                "Auto-Repel Selected Overlaps",
                lambda: patchcanvas.repelNodes(selected),
            )
            self.addSeparator()

            # Batch Operations
            btnBatchColor = self.addButton(
                icon_color, "Batch Color Selected Nodes...", lambda: None
            )
            btnBatchColor.clicked.disconnect()
            btnBatchColor.clicked.connect(
                lambda: self._slot_show_color_menu(btnBatchColor, selected)
            )

            self.addButton(
                icon_power,
                "Batch Toggle Power (Active)",
                lambda: self._slot_batch_power(selected),
            )
            self.addButton(
                icon_bypass,
                "Batch Toggle Bypass",
                lambda: self._slot_batch_bypass(selected),
            )
            self.addButton(
                icon_ports,
                "Batch Toggle Hide Unconnected Ports",
                lambda: self._slot_batch_hide_ports(selected),
            )
            self.addButton(
                icon_cut,
                "Disconnect All Cables on Selected Nodes",
                lambda: self._slot_disconnect_selected(selected),
            )
            # Group into Container
            btnGroup = self.addButton(icon_rack, "Group Selected Nodes into Container...", lambda: None)
            btnGroup.clicked.disconnect()
            btnGroup.clicked.connect(lambda: self._slot_show_group_create_menu(btnGroup))
            self.addSeparator()

            self.addButton(
                icon_inv, "Invert Selection", patchcanvas.invertNodeSelection
            )
            self.addButton(
                icon_desel, "Clear Selection (Esc)", patchcanvas.deselectAllNodes
            )

        # Grouped "Arrange tools" popover, always available so the bar stays uncluttered
        self.addSeparator()
        btnTools = self.addButton(
            icon_tools, "Arrange Tools: auto-arrange, auto-wire, repel", lambda: None
        )
        btnTools.clicked.disconnect()
        btnTools.clicked.connect(lambda: self._slot_show_arrange_menu(btnTools, count))

        # Box-model autolayout: children carry their own sizes (QSS tiles,
        # fixed search field, separators); the bar follows its layout hint and
        # never exceeds the canvas viewport.
        for w in self._items:
            w.show()
            w.ensurePolished()
        if search is not None and search.hasFocus():
            search.setFocus()
        self.layout.activate()
        self.setFixedHeight(32)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None and self.width() > parent.width() - 24:
            self.resize(parent.width() - 24, 32)
        if not getattr(self, "_userMoved", False):
            self.reposition()

    def _slot_show_color_menu(self, source_button, nodes):
        menu = QMenu(self)

        from patchcanvas.theme import get_swatch_colors
        theme = patchcanvas.canvas.theme
        presets = [("Default", theme.color_surface.name())]
        presets += [(label, colour) for colour, label in get_swatch_colors()]

        def create_color_icon(hex_str):
            pix = QPixmap(14, 14)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setBrush(QColor(hex_str))
            p.setPen(QColor(theme.color_muted))
            p.drawRoundedRect(1, 1, 12, 12, 3, 3)
            p.end()
            return QIcon(pix)

        for name, hex_code in presets:
            act = menu.addAction(create_color_icon(hex_code), name)
            act.triggered.connect(
                lambda checked, h=hex_code: self._apply_color_to_nodes(nodes, h)
            )

        menu.addSeparator()
        act_custom = menu.addAction("Custom Color Picker...")
        act_custom.triggered.connect(lambda: self._open_custom_color_dialog(nodes))

        act_reset = menu.addAction("Reset to Theme Default")
        act_reset.triggered.connect(lambda: self._apply_color_to_nodes(nodes, ""))

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_show_arrange_menu(self, source_button, count):
        menu = QMenu(self)

        has_selection = count > 0

        arrange_menu = menu.addMenu("Auto arrange")
        for algo_name, algo_label in patchcanvas.layout_algorithms():
            act = arrange_menu.addAction(algo_label)
            act.triggered.connect(
                lambda checked=False, a=algo_name: self._slot_run_arrange(a)
            )

        act_wire = menu.addAction("Auto wire")
        act_wire.triggered.connect(lambda: patchcanvas.autoWire())
        act_wire.setEnabled(has_selection)

        act_both = menu.addAction("Arrange + wire")
        act_both.triggered.connect(lambda: patchcanvas.autoArrangeAndWire())
        act_both.setEnabled(has_selection)

        menu.addSeparator()
        act_repel = menu.addAction(
            "Auto repel all" if not has_selection else "Auto repel selection"
        )
        act_repel.triggered.connect(lambda: patchcanvas.autoRepelNodes())

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_run_arrange(self, algorithm):
        patchcanvas.options.arrange_style = algorithm
        try:
            from utils import QSafeSettings
            from carla_shared import CARLA_KEY_CANVAS_ARRANGE_STYLE

            QSafeSettings("falkTX", "Carla2").setValue(
                CARLA_KEY_CANVAS_ARRANGE_STYLE, algorithm
            )
        except Exception:
            pass
        patchcanvas.autoArrangeNodes(algorithm=algorithm)

    def _apply_color_to_nodes(self, nodes, hex_str):
        for n in nodes:
            if hasattr(n, "setColor") and hasattr(n, "m_layout_mode"):
                n.setColor(hex_str if hex_str else patchcanvas.canvas.theme.color_accent)
                continue
            if hasattr(n, "setCustomColor"):
                n.setCustomColor(hex_str)
            pid = getattr(n, "m_plugin_id", -1)
            if 0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED:
                patchcanvas.canvas.callback(
                    patchcanvas.ACTION_PLUGIN_COLOR, pid, 0, hex_str
                )

    def _open_custom_color_dialog(self, nodes):
        initial = QColor(patchcanvas.canvas.theme.color_surface)
        if nodes:
            if hasattr(nodes[0], "m_color") and nodes[0].m_color:
                initial = nodes[0].m_color
            elif hasattr(nodes[0], "m_custom_color") and nodes[0].m_custom_color:
                initial = QColor(nodes[0].m_custom_color)
        color = QColorDialog.getColor(initial, self, "Choose Tint Color")
        if color.isValid():
            self._apply_color_to_nodes(nodes, color.name())

    def _slot_show_container_layout_menu(self, source_button, container):
        menu = QMenu(self)
        modes = [
            ("vbox", "VBox (Vertical)"),
            ("hbox", "HBox (Horizontal)"),
            ("grid", "Grid (Matrix)"),
            ("freeform", "Freeform (Unconstrained)"),
        ]
        cur = getattr(container, "m_layout_mode", "vbox")
        for mode_key, mode_name in modes:
            act = menu.addAction(mode_name)
            act.setCheckable(True)
            act.setChecked(cur == mode_key)
            act.triggered.connect(lambda checked=False, m=mode_key: (container.setLayoutMode(m), self.updateSelection()))

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_show_group_create_menu(self, source_button):
        menu = QMenu(self)
        modes = [
            ("vbox", "VBox (Vertical)"),
            ("hbox", "HBox (Horizontal)"),
            ("grid", "Grid (Matrix)"),
            ("freeform", "Freeform (Unconstrained)"),
        ]
        for mode_key, mode_name in modes:
            act = menu.addAction(mode_name)
            act.triggered.connect(lambda checked=False, m=mode_key: (patchcanvas.createContainerFromSelected(m), self.updateSelection()))

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_toggle_power(self, node):
        pid = getattr(node, "m_plugin_id", -1)
        if not (0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED):
            return
        try:
            from carla_shared import gCarla
            from carla_backend import PARAMETER_ACTIVE

            pwidget = (
                gCarla.gui.getPluginWidget(pid)
                if hasattr(gCarla.gui, "getPluginWidget")
                else None
            )
            if pwidget is not None and hasattr(pwidget, "fIsActive"):
                cur = bool(pwidget.fIsActive)
            elif hasattr(gCarla.gui, "host") and hasattr(
                gCarla.gui.host, "get_internal_parameter_value"
            ):
                cur = bool(
                    gCarla.gui.host.get_internal_parameter_value(pid, PARAMETER_ACTIVE)
                    >= 0.5
                )
            else:
                cur = True
            new_state = not cur
            gCarla.gui.host.set_active(pid, new_state)
            if pwidget is not None:
                pwidget.setActive(new_state, sendCallback=True, sendHost=False)
            if hasattr(node, "update"):
                node.update()
            scene = self.graphicsView.scene()
            if scene:
                scene.update()
        except Exception as e:
            print(f"CanvasContextToolBarOverlay::_slot_toggle_power error: {e}")

    def _slot_toggle_bypass(self, node):
        pid = getattr(node, "m_plugin_id", -1)
        if not (0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED):
            return
        try:
            from carla_shared import gCarla
            from carla_backend import PARAMETER_DRYWET

            pwidget = (
                gCarla.gui.getPluginWidget(pid)
                if hasattr(gCarla.gui, "getPluginWidget")
                else None
            )
            cur_val = gCarla.gui.host.get_internal_parameter_value(
                pid, PARAMETER_DRYWET
            )
            new_val = 1.0 if cur_val == 0.0 else 0.0
            gCarla.gui.host.set_drywet(pid, new_val)
            if pwidget is not None:
                pwidget.setParameterValue(PARAMETER_DRYWET, new_val, True)
                if hasattr(pwidget, "_update_bypass_state"):
                    pwidget._update_bypass_state(bool(new_val == 0.0))
            if hasattr(node, "update"):
                node.update()
            scene = self.graphicsView.scene()
            if scene:
                scene.update()
        except Exception as e:
            print(f"CanvasContextToolBarOverlay::_slot_toggle_bypass error: {e}")

    def _slot_batch_power(self, nodes):
        for n in nodes:
            self._slot_toggle_power(n)

    def _slot_batch_bypass(self, nodes):
        for n in nodes:
            self._slot_toggle_bypass(n)

    def _slot_batch_hide_ports(self, nodes):
        any_unhidden = any(
            not getattr(n, "m_hide_unconnected_ports", False) for n in nodes
        )
        for n in nodes:
            if hasattr(n, "setHideUnconnectedPorts"):
                n.setHideUnconnectedPorts(any_unhidden)
            else:
                n.m_hide_unconnected_ports = any_unhidden
                if hasattr(n, "updatePositions"):
                    n.updatePositions()
        scene = self.graphicsView.scene()
        if scene:
            scene.update()
        self.updateSelection()

    def _slot_toggle_hide_ports(self, node):
        new_val = not getattr(node, "m_hide_unconnected_ports", False)
        if hasattr(node, "setHideUnconnectedPorts"):
            node.setHideUnconnectedPorts(new_val)
        else:
            node.m_hide_unconnected_ports = new_val
            if hasattr(node, "updatePositions"):
                node.updatePositions()
            scene = self.graphicsView.scene()
            if scene:
                scene.update()
        self.updateSelection()

    def _slot_split_join(self, node):
        group_id = getattr(node, "m_group_id", -1)
        if group_id < 0:
            return
        if getattr(node, "m_split", False):
            patchcanvas.canvas.callback(patchcanvas.ACTION_GROUP_JOIN, group_id, 0, "")
        else:
            patchcanvas.canvas.callback(patchcanvas.ACTION_GROUP_SPLIT, group_id, 0, "")

    def _slot_disconnect_node(self, node):
        group_id = getattr(node, "m_group_id", -1)
        port_ids = set(getattr(node, "m_port_list_ids", []))
        conns_to_drop = []
        for c in patchcanvas.canvas.connection_list:
            if (c.group_out_id == group_id and c.port_out_id in port_ids) or (
                c.group_in_id == group_id and c.port_in_id in port_ids
            ):
                conns_to_drop.append(c.connection_id)
        for cid in conns_to_drop:
            patchcanvas.canvas.callback(patchcanvas.ACTION_PORTS_DISCONNECT, cid, 0, "")

    def _slot_disconnect_selected(self, nodes):
        node_groups_ports = set()
        for n in nodes:
            gid = getattr(n, "m_group_id", -1)
            for pid in getattr(n, "m_port_list_ids", []):
                node_groups_ports.add((gid, pid))
        conns_to_drop = []
        for c in patchcanvas.canvas.connection_list:
            if (c.group_out_id, c.port_out_id) in node_groups_ports or (
                c.group_in_id,
                c.port_in_id,
            ) in node_groups_ports:
                conns_to_drop.append(c.connection_id)
        for cid in conns_to_drop:
            patchcanvas.canvas.callback(patchcanvas.ACTION_PORTS_DISCONNECT, cid, 0, "")

    def _slot_arrange(self):
        patchcanvas.arrange()

    def _slot_repel_all(self):
        all_n = []
        for g in patchcanvas.canvas.group_list:
            for w in g.widgets:
                if w is not None and w.isVisible():
                    all_n.append(w)
        patchcanvas.repelNodes(all_n)

    def _slot_move_aside_all(self):
        patchcanvas.moveAsideNonConnectedNodes()

    def _slot_jump_rack(self, plugin_id):
        try:
            from carla_shared import gCarla

            if hasattr(gCarla.gui, "ui"):
                split_idx = gCarla.gui.ui.tabWidget.indexOf(
                    getattr(gCarla.gui, "tabSplit", None)
                )
                if split_idx >= 0:
                    gCarla.gui.ui.tabWidget.setCurrentIndex(split_idx)
                else:
                    gCarla.gui.ui.tabWidget.setCurrentIndex(0)
                pitem = gCarla.gui.getPluginItem(plugin_id)
                if pitem is not None and gCarla.gui.ui.listWidget is not None:
                    gCarla.gui.ui.listWidget.setCurrentItem(pitem)
                    gCarla.gui.ui.listWidget.scrollToItem(pitem)
        except Exception as e:
            print("Error jumping to rack:", e)

    def mousePressEvent(self, event):
        if _canvas_locked():
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self._dragPos = (
                _get_event_global_pos(event) - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if _canvas_locked():
            event.accept()
            return
        if self._dragPos is not None and event.buttons() & Qt.LeftButton:
            vp = self.parentWidget()
            if vp:
                new_pos = _get_event_global_pos(event) - self._dragPos
                x = max(0, min(new_pos.x(), vp.width() - self.width()))
                y = max(0, min(new_pos.y(), vp.height() - self.height()))
                self.move(x, y)
                self._userMoved = True
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragPos = None
        super().mouseReleaseEvent(event)

    def reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        if getattr(self, "_userMoved", False):
            # Keep the dragged position, but never let it leave the canvas.
            x = max(12, min(self.x(), parent.width() - self.width() - 12))
            y = max(12, min(self.y(), parent.height() - self.height() - 12))
            self.move(x, y)
            return
        # Top toolbar: pinned to the patchbay's top edge, horizontally centered.
        x = max(12, (parent.width() - self.width()) // 2)
        y = 12
        self.move(x, y)
        self.raise_()


# ------------------------------------------------------------------------------------------------------------
# Canvas Viewport Event Filter (Auto-Scroll & UI Disconnect)
# ------------------------------------------------------------------------------------------------------------
