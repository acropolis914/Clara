#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import json
import subprocess
from qt_compat import (
    pyqtSignal,
    pyqtSlot,
    qCritical,
    QT_VERSION,
    Qt,
    QPointF,
    QRectF,
    QTimer,
    QColor,
    QColorDialog,
    QCursor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QGraphicsSvgItem,
    QApplication,
    QGraphicsItem,
    QGraphicsObject,
    QMenu,
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QWidgetAction,
)

# ------------------------------------------------------------------------------------------------------------
# Backwards-compatible horizontalAdvance/width call, depending on Qt version


def fontHorizontalAdvance(font, string):
    if QT_VERSION >= 0x50B00:
        return QFontMetrics(font).horizontalAdvance(string)
    return QFontMetrics(font).width(string)


def getSystemFont(size=None, weight=None):
    base_font = QApplication.font() if QApplication.instance() else QFont()
    font = QFont(base_font)
    if size is not None and size > 0:
        font.setPixelSize(size)
    if weight is not None:
        font.setWeight(weight)
    return font


# ------------------------------------------------------------------------------------------------------------
# PipeWire Property Formatting Dictionary

PW_PRETTY_MAP = {
    # Application / Client
    "application.name": "Application Name",
    "application.process.id": "Process ID",
    "application.process.user": "Process User",
    "application.process.host": "Process Host",
    "application.process.binary": "Process Binary",
    "application.language": "Language",
    "client.api": "Client API",
    "client.id": "Client ID",
    # ALSA Specifics
    "alsa.card": "ALSA Card ID",
    "alsa.card_name": "ALSA Card Name",
    "alsa.class": "ALSA Class",
    "alsa.components": "ALSA Components",
    "alsa.device": "ALSA Device ID",
    "alsa.driver_name": "ALSA Driver Name",
    "alsa.id": "ALSA ID",
    "alsa.long_card_name": "ALSA Long Card Name",
    "alsa.mixer_name": "ALSA Mixer Name",
    "alsa.name": "ALSA Name",
    "alsa.resolution_bits": "ALSA Resolution (Bits)",
    "alsa.subclass": "ALSA Subclass",
    "alsa.subdevice": "ALSA Subdevice ID",
    "alsa.subdevice_name": "ALSA Subdevice Name",
    "alsa.sync.id": "ALSA Sync ID",
    "api.alsa.card.longname": "ALSA API Card Longname",
    "api.alsa.card.name": "ALSA API Card Name",
    "api.alsa.headroom": "ALSA API Headroom",
    "api.alsa.path": "ALSA API Path",
    "api.alsa.pcm.card": "ALSA PCM Card",
    "api.alsa.pcm.stream": "ALSA PCM Stream",
    "api.alsa.period-num": "ALSA Period Count",
    "api.alsa.period-size": "ALSA Period Size",
    # Audio & Clock
    "audio.channels": "Channels",
    "audio.rate": "Sample Rate",
    "audio.position": "Channel Map",
    "audio.format": "Audio Format",
    "clock.quantum-limit": "Quantum Limit",
    "clock.rate": "Clock Rate",
    "clock.allowed-rates": "Allowed Rates",
    # Device
    "card.profile.device": "Card Profile Device",
    "device.api": "Device API",
    "device.bus": "Device Bus",
    "device.class": "Device Class",
    "device.icon-name": "Device Icon",
    "device.id": "Device ID",
    "device.description": "Device Description",
    "device.name": "Device Name",
    "device.nick": "Device Nickname",
    "device.profile.description": "Device Profile Description",
    "device.profile.name": "Device Profile Name",
    "device.routes": "Device Routes",
    # Core / Internal
    "factory.name": "Factory Name",
    "factory.id": "Factory ID",
    "library.name": "Library Name",
    "object.id": "Object ID",
    "object.serial": "Object Serial",
    "object.path": "Object Path",
    # Media
    "media.class": "Media Class",
    "media.type": "Media Type",
    "media.role": "Media Role",
    "media.name": "Media Name",
    # Node
    "node.description": "Description",
    "node.name": "Node Name",
    "node.nick": "Nickname",
    "node.latency": "Latency",
    "node.max-latency": "Maximum Latency",
    "node.driver": "Is Driver",
    "node.driver-id": "Driver Node ID",
    "node.loop.name": "Loop Name",
    "node.pause-on-idle": "Pause on Idle",
    # Port & Stream
    "port.name": "Port Name",
    "port.direction": "Port Direction",
    "port.alias": "Port Alias",
    "port.group": "Port Group",
    "stream.is-live": "Is Live Stream",
    # Priority
    "priority.driver": "Driver Priority",
    "priority.session": "Session Priority",
}
# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    features,
    options,
    port_dict_t,
    CanvasBoxType,
    ANTIALIASING_FULL,
    ACTION_PLUGIN_EDIT,
    ACTION_PLUGIN_SHOW_UI,
    ACTION_PLUGIN_CLONE,
    ACTION_PLUGIN_REMOVE,
    ACTION_PLUGIN_RENAME,
    ACTION_PLUGIN_REPLACE,
    ACTION_GROUP_INFO,
    ACTION_GROUP_JOIN,
    ACTION_GROUP_SPLIT,
    ACTION_GROUP_RENAME,
    ACTION_PORTS_DISCONNECT,
    ACTION_INLINE_DISPLAY,
    EYECANDY_FULL,
    PORT_MODE_NULL,
    PORT_MODE_INPUT,
    PORT_MODE_OUTPUT,
    PORT_TYPE_NULL,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
    MAX_PLUGIN_ID_ALLOWED,
)

from .canvasboxshadow import CanvasBoxShadow
from .canvasicon import CanvasIcon
from .canvasport import CanvasPort
from .linealgos import active_line_algorithm_is_dynamic
from .theme import Theme
from .utils import (
    CanvasItemFX,
    CanvasGetFullPortName,
    CanvasGetPortConnectionList,
    log_carla,
)

# ------------------------------------------------------------------------------------------------------------


class cb_line_t(object):
    def __init__(self, line, connection_id):
        self.line = line
        self.connection_id = connection_id


# ------------------------------------------------------------------------------------------------------------


class BoxPropertiesDialog(QDialog):
    def __init__(self, box, parent=None):
        super().__init__(parent)
        self.box = box
        self.setWindowTitle(f"{box.getGroupName()} Properties")
        self.resize(520, 680)

        # Fetch PipeWire properties early using the node's query name
        query_name = (
            getattr(self.box, "pw_node_name", None)
            or self.box.getGroupName()
        )
        self.pw_props = self.get_pw_properties(query_name)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Tabs
        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.ports_tab = QWidget()
        self.pw_tab = QWidget()

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.ports_tab, "Ports")
        self.tabs.addTab(self.pw_tab, "PipeWire Raw")

        layout.addWidget(self.tabs)

        self.setup_general_tab()
        self.setup_ports_tab()
        self.setup_pipewire_tab()

        # Bottom Buttons (OK, Cancel, Apply)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.apply_changes
        )
        layout.addWidget(self.button_box)

    def get_pw_properties(self, search_name):
        try:
            # 1. Try querying pw-dump directly with search_name (pw-dump accepts node.name or id)
            if search_name:
                try:
                    out = subprocess.check_output(
                        ["pw-dump", str(search_name)],
                        text=True,
                        stderr=subprocess.DEVNULL,
                    )
                    if out.strip():
                        data = json.loads(out)
                        for obj in data:
                            if obj.get("type") in (
                                "PipeWire:Interface:Node",
                                "PipeWire:Interface:Client",
                            ):
                                props = obj.get("info", {}).get("props", {})
                                if props:
                                    if "node.name" in props and hasattr(self.box, "pw_node_name"):
                                        self.box.pw_node_name = props["node.name"]
                                    return props
                except (subprocess.SubprocessError, json.JSONDecodeError):
                    pass

            # 2. Fall back to dumping state and matching against node names, descriptions, or nicks
            out = subprocess.check_output(["pw-dump"], text=True, stderr=subprocess.DEVNULL)
            state = json.loads(out)

            box_title = self.box.getGroupName() if hasattr(self.box, "getGroupName") else ""
            for obj in state:
                if obj.get("type") in (
                    "PipeWire:Interface:Node",
                    "PipeWire:Interface:Client",
                ):
                    props = obj.get("info", {}).get("props", {})
                    candidates = (
                        props.get("node.name"),
                        props.get("node.description"),
                        props.get("node.nick"),
                        props.get("client.name"),
                        props.get("application.name"),
                        props.get("media.name"),
                    )

                    if (search_name and search_name in candidates) or (
                        box_title and box_title in candidates
                    ):
                        if "node.name" in props and hasattr(self.box, "pw_node_name"):
                            self.box.pw_node_name = props["node.name"]
                        return props

        except Exception as e:
            print(f"Failed to fetch PipeWire data: {e}")

        return None

    def create_group_box(self, title):
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 13px;
                padding-top: 18px; 
                margin-top: 12px;
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 4px;
            } 
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px 0 5px;
            }
        """)
        return group

    def setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- 1. Header (H1 Equivalent) ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        icon_label = QLabel()
        icon_label.setPixmap(
            self.style()
            .standardIcon(self.style().StandardPixmap.SP_FileIcon)
            .pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        self.name_edit = QLineEdit(self.box.getGroupName())
        font = self.name_edit.font()
        font.setPointSize(16)
        font.setBold(True)
        self.name_edit.setFont(font)
        self.name_edit.setStyleSheet("""
            QLineEdit { 
                border: 1px solid transparent; 
                border-bottom: 1px solid rgba(128, 128, 128, 0.4); 
                background: transparent; 
                padding: 0px;
                margin-bottom: 2px;
            } 
            QLineEdit:focus { 
                border-bottom: 2px solid palette(highlight); 
            }
        """)
        title_layout.addWidget(self.name_edit)

        type_str = "Plugin Node" if self.box.m_plugin_id >= 0 else "Canvas Group"
        type_subtitle = QLabel(
            f"<span style='color: #777; font-size: 11pt;'>{type_str}</span>"
        )
        title_layout.addWidget(type_subtitle)
        title_layout.addStretch()

        header_layout.addLayout(title_layout)
        layout.addLayout(header_layout)

        # Separator
        line1 = QFrame()
        line1.setFrameShape(
            QFrame.Shape.HLine if hasattr(QFrame, "Shape") else QFrame.HLine
        )
        line1.setFrameShadow(
            QFrame.Shadow.Sunken if hasattr(QFrame, "Shadow") else QFrame.Sunken
        )
        layout.addWidget(line1)

        # --- 2. PipeWire Identity Box (Most Important) ---
        if self.pw_props:
            pw_group = self.create_group_box("PipeWire Identity")
            pw_layout = QFormLayout(pw_group)
            pw_layout.setSpacing(8)
            pw_layout.setContentsMargins(15, 15, 15, 15)

            desc = self.pw_props.get(
                "node.description", self.pw_props.get("node.nick", "N/A")
            )
            media_class = self.pw_props.get("media.class", "N/A")
            app_name = self.pw_props.get("application.name", "N/A")
            node_name = self.pw_props.get("node.name", "N/A")

            lbl_desc = QLabel(
                f"<span style='font-size: 11pt; font-weight: bold;'>{desc}</span>"
            )
            lbl_desc.setWordWrap(True)

            pw_layout.addRow("Description:", lbl_desc)

            if media_class != "N/A":
                pw_layout.addRow(
                    "Media Class:",
                    QLabel(
                        f"<code style='color: #2b78e4; font-size: 10pt;'>{media_class}</code>"
                    ),
                )

            if app_name != "N/A":
                pw_layout.addRow("Application:", QLabel(f"<b>{app_name}</b>"))

            pw_layout.addRow("Node Name:", QLabel(str(node_name)))
            layout.addWidget(pw_group)

        # --- 3. Node Identity Box ---
        info_group = self.create_group_box("Node Details")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(15, 15, 15, 15)

        info_layout.addRow("Canvas Group ID:", QLabel(str(self.box.getGroupId())))
        if self.box.m_plugin_id >= 0:
            info_layout.addRow("Plugin ID:", QLabel(f"<b>{self.box.m_plugin_id}</b>"))
            info_layout.addRow(
                "Custom UI:",
                QLabel("<b>Available</b>" if self.box.m_plugin_ui else "Not Available"),
            )

        layout.addWidget(info_group)

        # --- 4. Geometry Box (Least Important) ---
        geo_group = self.create_group_box("Geometry & Layout")
        geo_layout = QFormLayout(geo_group)
        geo_layout.setSpacing(8)
        geo_layout.setContentsMargins(15, 15, 15, 15)

        geo_layout.addRow(
            "Position (X, Y):", QLabel(f"{int(self.box.x())}, {int(self.box.y())}")
        )
        geo_layout.addRow(
            "Dimensions:",
            QLabel(f"{int(self.box.p_width)}w × {int(self.box.p_height)}h pixels"),
        )
        geo_layout.addRow(
            "Split Mode:",
            QLabel(
                "<span style='color: #2e8b57; font-weight: bold;'>Active</span>"
                if self.box.isSplit()
                else "Inactive"
            ),
        )

        layout.addWidget(geo_group)
        layout.addStretch()

    def setup_ports_tab(self):
        layout = QVBoxLayout(self.ports_tab)
        layout.setContentsMargins(15, 15, 15, 15)

        port_group = self.create_group_box("Port Configuration")
        form = QFormLayout(port_group)
        form.setSpacing(12)
        form.setContentsMargins(15, 20, 15, 15)

        form.addRow(
            "Total Ports:",
            QLabel(
                f"<span style='font-size: 12pt; font-weight: bold;'>{self.box.getPortCount()}</span>"
            ),
        )

        # Count inputs and outputs
        ins = outs = 0
        for port in canvas.port_list:
            if (
                port.widget.parentItem() == self.box
                and port.port_id in self.box.m_port_list_ids
            ):
                if port.port_mode == PORT_MODE_INPUT:
                    ins += 1
                elif port.port_mode == PORT_MODE_OUTPUT:
                    outs += 1

        form.addRow("Input Ports:", QLabel(str(ins)))
        form.addRow("Output Ports:", QLabel(str(outs)))

        layout.addWidget(port_group)
        layout.addStretch()

    def setup_pipewire_tab(self):
        layout = QVBoxLayout(self.pw_tab)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        if not self.pw_props:
            target_str = f"<b>{self.box.getGroupName()}</b>"
            if getattr(self.box, "pw_node_name", None) and self.box.pw_node_name != self.box.getGroupName():
                target_str += f" (<code>{self.box.pw_node_name}</code>)"
            lbl = QLabel(
                f"Could not find matching PipeWire properties for {target_str}.<br><br>Ensure the node is active and named identically in the PipeWire graph."
            )
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            layout.addStretch()
            return

        # Top Controls Layout
        controls_layout = QHBoxLayout()

        self.pretty_checkbox = QCheckBox("Show user-friendly property names")
        self.pretty_checkbox.setChecked(True)
        self.pretty_checkbox.toggled.connect(self.populate_pw_table)
        controls_layout.addWidget(self.pretty_checkbox)

        controls_layout.addStretch()

        self.btn_copy = QPushButton("Copy JSON")
        self.btn_copy.setToolTip("Copy raw PipeWire JSON to clipboard")
        self.btn_copy.clicked.connect(self.copy_pw_json)
        controls_layout.addWidget(self.btn_copy)

        layout.addLayout(controls_layout)

        # Create a table to show properties
        self.pw_table = QTableWidget(0, 2)
        self.pw_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.pw_table.horizontalHeader().setStretchLastSection(True)
        self.pw_table.setColumnWidth(0, 200)
        self.pw_table.verticalHeader().setVisible(False)
        self.pw_table.setAlternatingRowColors(True)

        # Reduce vertical padding in rows
        self.pw_table.verticalHeader().setDefaultSectionSize(24)

        # Disable editing
        if hasattr(QTableWidget, "EditTrigger"):
            self.pw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        else:
            self.pw_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.pw_table)

        # Initial population
        self.populate_pw_table()

    def populate_pw_table(self):
        if not hasattr(self, "pw_table") or not self.pw_props:
            return

        use_pretty = self.pretty_checkbox.isChecked()
        self.pw_table.setRowCount(0)
        self.pw_table.setRowCount(len(self.pw_props))

        for i, (key, val) in enumerate(sorted(self.pw_props.items())):
            display_key = PW_PRETTY_MAP.get(key, key) if use_pretty else key

            key_item = QTableWidgetItem(str(display_key))
            # Keep original raw key in tooltip for power users
            key_item.setToolTip(str(key))

            val_item = QTableWidgetItem(str(val))
            val_item.setToolTip(str(val))

            self.pw_table.setItem(i, 0, key_item)
            self.pw_table.setItem(i, 1, val_item)

    def copy_pw_json(self):
        if self.pw_props:
            QApplication.clipboard().setText(json.dumps(self.pw_props, indent=4))
            self.btn_copy.setText("Copied!")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copy JSON"))

    def apply_changes(self):
        # Update name if changed
        new_name = self.name_edit.text()
        if new_name != self.box.getGroupName():
            self.box.setGroupName(new_name)
            self.setWindowTitle(f"{new_name} Properties")

    def accept(self):
        self.apply_changes()
        super().accept()


# ------------------------------------------------------------------------------------------------------------


def _run_global_line_reroute():
    canvas._line_reroute_pending = False
    for connection in canvas.connection_list:
        connection.widget.updateLinePos()


def _schedule_global_line_reroute():
    if getattr(canvas, "_line_reroute_pending", False):
        return
    canvas._line_reroute_pending = True
    QTimer.singleShot(0, _run_global_line_reroute)


class CanvasBox(QGraphicsObject):
    # signals
    positionChanged = pyqtSignal(int, bool, int, int)

    # enums
    INLINE_DISPLAY_DISABLED = 0
    INLINE_DISPLAY_ENABLED = 1
    INLINE_DISPLAY_CACHED = 2

    # Box Width Limits
    MIN_BOX_WIDTH = 120  # Sensible minimum width
    MAX_BOX_WIDTH_TITLE = 200  # Max width driven by the title
    MAX_BOX_WIDTH_ABSOLUTE = 350  # Absolute hard limit for the box

    def __init__(self, group_id, group_name, icon, parent=None, pw_node_name=None):
        QGraphicsObject.__init__(self)
        self.setParentItem(parent)

        # Save Variables, useful for later
        self.m_group_id = group_id
        self.m_group_name = group_name
        self.setToolTip(self.m_group_name)

        # PipeWire accepted query name for nodes (node.name)
        self.pw_node_name = pw_node_name or group_name

        # plugin Id, < 0 if invalid
        self.m_plugin_id = -1
        self.m_plugin_ui = False
        self.m_plugin_inline = self.INLINE_DISPLAY_DISABLED

        # Custom node color / tinting
        self.m_custom_color = None

        # Base Variables
        self.p_width = 50
        self.p_width_in = 0
        self.p_width_out = 0
        self.p_height = (
            canvas.theme.box_header_height + canvas.theme.box_header_spacing + 1
        )

        self.m_last_pos = QPointF()
        self.m_split = False
        self.m_split_mode = PORT_MODE_NULL

        self.m_cursor_moving = False
        self.m_forced_split = False
        self.m_mouse_down = False
        self.m_inline_image = None
        self.m_inline_scaling = 1.0
        self.m_inline_first = True
        self.m_will_signal_pos_change = False

        self.m_port_list_ids = []
        self.m_connection_lines = []
        self.m_search_highlight = 0  # 0: None, 1: Matched (sapphire), 2: Active/Hovered (bright blue)
        self.m_hover_btn_id = None
        self.m_pressed_btn_id = None
        self.m_hide_unconnected_ports = False

        # Set Font
        self.m_font_name = getSystemFont(
            canvas.theme.box_font_size, canvas.theme.box_font_state
        )
        self.m_font_port = getSystemFont(
            canvas.theme.port_font_size, canvas.theme.port_font_state
        )

        self.setAcceptHoverEvents(True)
        # Icon
        if canvas.theme.box_use_icon:
            self.icon_svg = CanvasIcon(icon, self.m_group_name, self)
        else:
            self.icon_svg = None

        # Shadow
        if options.eyecandy and not options.software_render and QT_VERSION >= 0x50C00:
            self.shadow = CanvasBoxShadow(self.toGraphicsObject())
            self.shadow.setFakeParent(self)
            self.setGraphicsEffect(self.shadow)
        else:
            self.shadow = None

        # Final touches
        self.setFlags(
            QGraphicsItem.ItemIsFocusable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setCacheMode(
            getattr(QGraphicsItem, "DeviceCoordinateCache", getattr(getattr(QGraphicsItem, "CacheMode", None), "DeviceCoordinateCache", None))
        )

        # Wait for at least 1 port
        if options.auto_hide_groups:
            self.setVisible(False)

        if options.auto_select_items:
            self.setAcceptHoverEvents(True)

        self.updatePositions()

        self.visibleChanged.connect(self.slot_signalPositionChangedLater)
        self.xChanged.connect(self.slot_signalPositionChangedLater)
        self.yChanged.connect(self.slot_signalPositionChangedLater)

        canvas.scene.addItem(self)
        QTimer.singleShot(0, self.fixPos)

    def showPropertiesDialog(self):
        parent_view = (
            self.scene().views()[0] if self.scene() and self.scene().views() else None
        )
        self.prop_dialog = BoxPropertiesDialog(self, parent_view)
        self.prop_dialog.show()

    def getGroupId(self):
        return self.m_group_id

    def getGroupName(self):
        return self.m_group_name

    def getPwNodeName(self):
        return self.pw_node_name

    def setPwNodeName(self, name):
        self.pw_node_name = name

    @property
    def node_name(self):
        return self.pw_node_name

    @node_name.setter
    def node_name(self, value):
        self.pw_node_name = value

    def isSplit(self):
        return self.m_split

    def setHideUnconnectedPorts(self, hide):
        self.m_hide_unconnected_ports = bool(hide)
        self.updatePositions()
        if hasattr(self, "scene") and self.scene():
            self.scene().update()

    def setCustomColor(self, color, notify=True):
        self.m_custom_color = QColor(color) if color else None
        self.update()
        self.repaintLines(True)
        if hasattr(self, "scene") and self.scene():
            self.scene().update()
        if notify:
            if self.m_plugin_id >= 0:
                color_str = color if color else ""
                canvas.callback(17, self.m_plugin_id, 0, color_str)  # 17 = ACTION_PLUGIN_COLOR
            else:
                try:
                    from carla_shared import gCarla
                    if hasattr(gCarla, "gui"):
                        gCarla.gui.fHasUnsavedChanges = True
                        if hasattr(gCarla.gui, "markProjectModified"):
                            gCarla.gui.markProjectModified()
                except Exception:
                    pass

    def getCustomColor(self):
        return self.m_custom_color

    def getSplitMode(self):
        return self.m_split_mode

    def getNodeBadgeType(self):
        if self.m_plugin_id >= 0:
            try:
                from carla_shared import gCarla
                from carla_skin import CATEGORY_BADGES
                pinfo = gCarla.gui.host.get_plugin_info(self.m_plugin_id)
                cat = pinfo.get("category", 0)
                if cat in CATEGORY_BADGES:
                    return CATEGORY_BADGES[cat][0]
                hints = pinfo.get("hints", 0)
                from carla_backend import PLUGIN_IS_SYNTH
                if hints & PLUGIN_IS_SYNTH:
                    return "SYNTH"
                return "PLUGIN"
            except Exception:
                return "PLUGIN"

        has_ins = False
        has_outs = False
        pid_set = set(self.m_port_list_ids)
        for port in canvas.port_list:
            if port.port_id in pid_set:
                if getattr(port, "port_mode", None) == PORT_MODE_INPUT:
                    has_ins = True
                elif getattr(port, "port_mode", None) == PORT_MODE_OUTPUT:
                    has_outs = True

        low_name = self.m_group_name.lower()
        if self.m_split_mode == PORT_MODE_INPUT or (has_ins and not has_outs):
            if any(k in low_name for k in ("sink", "playback", "speaker", "headphone")):
                return "SINK"
            return "IN"
        elif self.m_split_mode == PORT_MODE_OUTPUT or (has_outs and not has_ins):
            if any(k in low_name for k in ("source", "capture", "mic")):
                return "SOURCE"
            return "OUT"
        elif getattr(self, "m_icon", None) == 1 or any(k in low_name for k in ("system", "hardware", "alsa", "hw:")):
            return "HW"
        elif has_ins and has_outs:
            return "APP"
        return "NODE"

    def getPortCount(self):
        return len(self.m_port_list_ids)

    def getPortList(self):
        return self.m_port_list_ids

    def redrawInlineDisplay(self):
        if self.m_plugin_inline == self.INLINE_DISPLAY_CACHED:
            self.m_plugin_inline = self.INLINE_DISPLAY_ENABLED
            self.update()

    def removeAsPlugin(self):
        self.m_plugin_id = -1
        self.m_plugin_ui = False
        self.m_plugin_inline = self.INLINE_DISPLAY_DISABLED

    def setAsPlugin(self, plugin_id, hasUI, hasInlineDisplay):
        if hasInlineDisplay and not options.inline_displays:
            hasInlineDisplay = False

        if not hasInlineDisplay:
            self.m_inline_image = None
            self.m_inline_scaling = 1.0

        self.m_plugin_id = plugin_id
        self.m_plugin_ui = hasUI
        self.m_plugin_inline = (
            self.INLINE_DISPLAY_ENABLED
            if hasInlineDisplay
            else self.INLINE_DISPLAY_DISABLED
        )
        self.update()

    def setIcon(self, icon):
        if self.icon_svg is not None:
            self.icon_svg.setIcon(icon, self.m_group_name)

    def setSplit(self, split, mode=PORT_MODE_NULL):
        self.m_split = split
        self.m_split_mode = mode

    def setGroupName(self, group_name):
        self.m_group_name = group_name
        self.setToolTip(self.m_group_name)
        self.updatePositions()

    def setShadowOpacity(self, opacity):
        if self.shadow is not None:
            self.shadow.setOpacity(opacity)

    def addPortFromGroup(
        self,
        port_id,
        port_mode,
        port_type,
        port_name,
        is_alternate,
        backend_group_id=None,
    ):
        if len(self.m_port_list_ids) == 0:
            if options.auto_hide_groups:
                log_carla(
                    f"CanvasBox.addPortFromGroup: unhiding box '{self.m_group_name}' (id={self.m_group_id}) on first port '{port_name}'",
                    level="debug"
                )
                if options.eyecandy == EYECANDY_FULL:
                    CanvasItemFX(self, True, False)
                self.blockSignals(True)
                self.setVisible(True)
                self.blockSignals(False)

        new_widget = CanvasPort(
            self.m_group_id if backend_group_id is None else backend_group_id,
            port_id,
            port_name,
            port_mode,
            port_type,
            is_alternate,
            self,
        )

        port_dict = port_dict_t()
        port_dict.group_id = self.m_group_id
        port_dict.port_id = port_id
        port_dict.port_name = port_name
        port_dict.port_mode = port_mode
        port_dict.port_type = port_type
        port_dict.is_alternate = is_alternate
        port_dict.widget = new_widget
        new_widget._port_dict = port_dict

        self.m_port_list_ids.append(port_id)

        return new_widget

    def removePortFromGroup(self, port_id):
        if port_id in self.m_port_list_ids:
            self.m_port_list_ids.remove(port_id)
        else:
            qCritical(
                "PatchCanvas::CanvasBox.removePort(%i) - unable to find port to remove"
                % port_id
            )
            return

        if len(self.m_port_list_ids) > 0:
            self.updatePositions()

        elif self.isVisible():
            if options.auto_hide_groups:
                if options.eyecandy == EYECANDY_FULL:
                    CanvasItemFX(self, False, False)
                else:
                    self.blockSignals(True)
                    self.setVisible(False)
                    self.blockSignals(False)

    def addLineFromGroup(self, line, connection_id):
        new_cbline = cb_line_t(line, connection_id)
        self.m_connection_lines.append(new_cbline)

    def removeLineFromGroup(self, connection_id):
        for connection in self.m_connection_lines:
            if connection.connection_id == connection_id:
                self.m_connection_lines.remove(connection)
                return
        qCritical(
            "PatchCanvas::CanvasBox.removeLineFromGroup(%i) - unable to find line to remove"
            % connection_id
        )

    def checkItemPos(self):
        # In infinite canvas mode, expand canvas boundaries dynamically instead of clamping nodes
        pos = self.scenePos()
        node_rect = QRectF(pos.x(), pos.y(), self.p_width, self.p_height)

        if canvas.size_rect.isNull():
            canvas.size_rect = QRectF(node_rect)
        elif not canvas.size_rect.contains(node_rect):
            # Grow size_rect to envelop the node plus margin
            margin = 500.0
            expanded_rect = canvas.size_rect.united(
                QRectF(
                    node_rect.x() - margin,
                    node_rect.y() - margin,
                    node_rect.width() + 2 * margin,
                    node_rect.height() + 2 * margin,
                )
            )
            canvas.size_rect = expanded_rect
            if canvas.scene:
                canvas.scene.setSceneRect(expanded_rect)
                canvas.scene.updateLimits()

    def removeIconFromScene(self):
        if self.icon_svg is None:
            return

        item = self.icon_svg
        self.icon_svg = None
        canvas.scene.removeItem(item)
        del item

    def updatePositions(self):
        self.prepareGeometryChange()

        # Check Text Name size with Hard & Soft Limits
        # Add 30px buffer for margins/icons
        app_name_size = fontHorizontalAdvance(self.m_font_name, self.m_group_name) + 30

        # Apply configurable minimum width and title maximum width
        min_width = getattr(options, "node_min_width", self.MIN_BOX_WIDTH)
        max_title_width = max(self.MAX_BOX_WIDTH_TITLE, min_width)
        self.p_width = max(
            min_width, min(app_name_size, max_title_width)
        )

        # Get Port List: check canvas.port_list and fallback to direct child CanvasPort widgets
        port_list = []
        port_seen_ids = set()
        for port in canvas.port_list:
            if (
                port.widget.parentItem() == self
                and port.port_id in self.m_port_list_ids
            ):
                port_list.append(port)
                port_seen_ids.add((port.port_mode, port.port_id))

        # Check any child CanvasPort items that might not yet be in canvas.port_list
        for child in self.childItems():
            if isinstance(child, CanvasPort) and hasattr(child, "_port_dict"):
                pd = child._port_dict
                if (pd.port_mode, pd.port_id) not in port_seen_ids:
                    port_list.append(pd)
                    port_seen_ids.add((pd.port_mode, pd.port_id))

        # Filter connected vs unconnected if hide_unconnected_ports is enabled
        connected_port_ids = set()
        if getattr(self, "m_hide_unconnected_ports", False):
            # 1. Check globally tracked connections
            for conn in canvas.connection_list:
                if conn.group_out_id == self.m_group_id:
                    connected_port_ids.add((PORT_MODE_OUTPUT, conn.port_out_id))
                if conn.group_in_id == self.m_group_id:
                    connected_port_ids.add((PORT_MODE_INPUT, conn.port_in_id))

            # 2. Check connections attached directly to this CanvasBox
            for cbline in getattr(self, "m_connection_lines", []):
                line_widget = getattr(cbline, "line", None)
                if line_widget:
                    item1 = getattr(line_widget, "item1", None)
                    item2 = getattr(line_widget, "item2", None)
                    if item1 and hasattr(item1, "getPortId") and hasattr(item1, "getPortMode"):
                        if item1.parentItem() == self or getattr(item1, "m_group_id", None) == self.m_group_id:
                            connected_port_ids.add((item1.getPortMode(), item1.getPortId()))
                    if item2 and hasattr(item2, "getPortId") and hasattr(item2, "getPortMode"):
                        if item2.parentItem() == self or getattr(item2, "m_group_id", None) == self.m_group_id:
                            connected_port_ids.add((item2.getPortMode(), item2.getPortId()))

        visible_port_list = []
        for port in port_list:
            is_connected = (
                (port.port_mode, port.port_id) in connected_port_ids
                or (hasattr(port, "widget") and (port.widget.getPortMode(), port.widget.getPortId()) in connected_port_ids)
            )
            if getattr(self, "m_hide_unconnected_ports", False) and not is_connected:
                port.widget.setVisible(False)
            else:
                port.widget.setVisible(True)
                visible_port_list.append(port)

        subbar_h = 22 if self.m_plugin_id >= 0 else 0
        header_total_h = canvas.theme.box_header_height + subbar_h

        if len(visible_port_list) == 0:
            self.p_height = header_total_h + canvas.theme.box_header_spacing + 4
            self.p_width_in = 0
            self.p_width_out = 0
        else:
            max_in_width = max_out_width = 0
            port_spacing = canvas.theme.port_height + canvas.theme.port_spacing

            # Get Max Box Width, vertical ports re-positioning
            port_types = (
                PORT_TYPE_AUDIO_JACK,
                PORT_TYPE_MIDI_JACK,
                PORT_TYPE_MIDI_ALSA,
                PORT_TYPE_PARAMETER,
            )
            last_in_type = last_out_type = PORT_TYPE_NULL
            last_in_pos = last_out_pos = (
                header_total_h + canvas.theme.box_header_spacing
            )

            for port_type in port_types:
                for port in visible_port_list:
                    if port.port_type != port_type:
                        continue

                    size = fontHorizontalAdvance(self.m_font_port, port.port_name)

                    if port.port_mode == PORT_MODE_INPUT:
                        max_in_width = max(max_in_width, size)
                        if port.port_type != last_in_type:
                            if last_in_type != PORT_TYPE_NULL:
                                last_in_pos += canvas.theme.port_spacingT
                            last_in_type = port.port_type
                        port.widget.setY(last_in_pos)
                        last_in_pos += port_spacing

                    elif port.port_mode == PORT_MODE_OUTPUT:
                        max_out_width = max(max_out_width, size)
                        if port.port_type != last_out_type:
                            if last_out_type != PORT_TYPE_NULL:
                                last_out_pos += canvas.theme.port_spacingT
                            last_out_type = port.port_type
                        port.widget.setY(last_out_pos)
                        last_out_pos += port_spacing

            self.p_width = max(self.p_width, (100 if self.m_plugin_inline != self.INLINE_DISPLAY_DISABLED else 30) + max_in_width + max_out_width)
            self.p_width = min(
                self.p_width, self.MAX_BOX_WIDTH_ABSOLUTE
            )  # Absolute hard limit
            self.p_width_in = max_in_width
            self.p_width_out = max_out_width

            min_h = (header_total_h + 60) if self.m_plugin_inline != self.INLINE_DISPLAY_DISABLED else 0
            self.p_height = max(last_in_pos, last_out_pos, min_h)
            self.p_height += (
                max(canvas.theme.port_spacing, canvas.theme.port_spacingT)
                - canvas.theme.port_spacing
            )
            self.p_height += canvas.theme.box_pen.width()

            self.repositionPorts(visible_port_list)

        self.repaintLines(True)
        self.update()

    def calculateBoxSize(self):
        self.updatePositions()

    def repositionPorts(self, port_list=None):
        if port_list is None:
            port_list = []
            for port in canvas.port_list:
                if (
                    port.widget.parentItem() == self
                    and port.port_id in self.m_port_list_ids
                ):
                    port_list.append(port)

        # Horizontal ports re-positioning
        inX = canvas.theme.port_offset
        outX = self.p_width - self.p_width_out - canvas.theme.port_offset - 12
        for port in port_list:
            if port.port_mode == PORT_MODE_INPUT:
                port.widget.setX(inX)
                port.widget.setPortWidth(self.p_width_in)

            elif port.port_mode == PORT_MODE_OUTPUT:
                port.widget.setX(outX)
                port.widget.setPortWidth(self.p_width_out)

    def repaintLines(self, forced=False):
        if self.pos() != self.m_last_pos or forced:
            for connection in self.m_connection_lines:
                connection.line.updateLinePos()

            # Dynamic algorithms read global context, so every cable must re-route.
            # Coalesce to once per event-loop tick to avoid O(cables) work per move event.
            if active_line_algorithm_is_dynamic():
                _schedule_global_line_reroute()

        self.m_last_pos = self.pos()

    def updateConnectionSelectionState(self):
        """
        Refresh the selection state of the cables attached to this node.

        Focusing a node must immediately highlight and re-route its cables; otherwise they keep
        their stale look until the node happens to be moved.
        """
        for connection in self.m_connection_lines:
            try:
                connection.line.updateLineSelected()
            except Exception:
                pass

    def resetLinesZValue(self):
        for connection in canvas.connection_list:
            if (
                connection.port_out_id in self.m_port_list_ids
                and connection.port_in_id in self.m_port_list_ids
            ):
                z_value = canvas.last_z_value
            else:
                z_value = canvas.last_z_value - 1

            connection.widget.setZValue(z_value)

    def triggerSignalPositionChanged(self):
        self.positionChanged.emit(
            self.m_group_id, self.m_split, int(self.x()), int(self.y())
        )
        self.m_will_signal_pos_change = False

    @pyqtSlot()
    def slot_signalPositionChangedLater(self):
        # While dragging, defer engine/settings position updates until the drag
        # finishes. Emitting on every move causes a synchronous settings write
        # plus an engine callback per frame, which makes dragging feel laggy.
        if getattr(canvas, "dragging", False):
            return
        if self.m_will_signal_pos_change:
            return
        self.m_will_signal_pos_change = True
        QTimer.singleShot(0, self.triggerSignalPositionChanged)

    def type(self):
        return CanvasBoxType

    def contextMenuEvent(self, event):
        event.accept()
        menu = QMenu()

        # Conenct menu stuff
        connMenu = QMenu("Connect", menu)

        our_port_types = []
        our_port_outs = {
            PORT_TYPE_AUDIO_JACK: [],
            PORT_TYPE_MIDI_JACK: [],
            PORT_TYPE_MIDI_ALSA: [],
            PORT_TYPE_PARAMETER: [],
        }
        for port in canvas.port_list:
            if port.widget.parentItem() != self:
                continue
            if port.port_mode != PORT_MODE_OUTPUT:
                continue
            if port.port_id not in self.m_port_list_ids:
                continue
            if port.port_type not in our_port_types:
                our_port_types.append(port.port_type)
            our_port_outs[port.port_type].append((port.group_id, port.port_id))

        if len(our_port_types) != 0:
            act_x_conn = None
            for group in canvas.group_list:
                if self.m_group_id == group.group_id:
                    continue

                has_ports = False
                target_ports = {
                    PORT_TYPE_AUDIO_JACK: [],
                    PORT_TYPE_MIDI_JACK: [],
                    PORT_TYPE_MIDI_ALSA: [],
                    PORT_TYPE_PARAMETER: [],
                }

                for port in canvas.port_list:
                    if port.widget.parentItem() != group.widgets[0] and (
                        not group.split or port.widget.parentItem() != group.widgets[1]
                    ):
                        continue
                    if port.port_mode != PORT_MODE_INPUT:
                        continue
                    if port.port_type not in our_port_types:
                        continue
                    has_ports = True
                    target_ports[port.port_type].append((port.group_id, port.port_id))

                if not has_ports:
                    continue

                act_x_conn = connMenu.addAction(group.group_name)
                act_x_conn.setData((our_port_outs, target_ports))
                act_x_conn.triggered.connect(canvas.qobject.PortContextMenuConnect)

            if act_x_conn is None:
                act_x_disc = connMenu.addAction("Nothing to connect to")
                act_x_disc.setEnabled(False)

        else:
            act_x_disc = connMenu.addAction("No output ports")
            act_x_disc.setEnabled(False)

        # Disconnect menu stuff
        discMenu = QMenu("Disconnect", menu)

        conn_list = []
        conn_list_ids = []

        for port_id in self.m_port_list_ids:
            tmp_conn_list = CanvasGetPortConnectionList(self.m_group_id, port_id)
            for tmp_conn_id, tmp_group_id, tmp_port_id in tmp_conn_list:
                if tmp_conn_id not in conn_list_ids:
                    conn_list.append((tmp_conn_id, tmp_group_id, tmp_port_id))
                    conn_list_ids.append(tmp_conn_id)

        if len(conn_list) > 0:
            for conn_id, group_id, port_id in conn_list:
                act_x_disc = discMenu.addAction(
                    CanvasGetFullPortName(group_id, port_id)
                )
                act_x_disc.setData(conn_id)
                act_x_disc.triggered.connect(canvas.qobject.PortContextMenuDisconnect)
        else:
            act_x_disc = discMenu.addAction("No connections")
            act_x_disc.setEnabled(False)

        menu.addMenu(connMenu)
        menu.addMenu(discMenu)
        act_x_disc_all = menu.addAction("Disconnect &All")
        act_x_sep1 = menu.addSeparator()
        act_x_info = menu.addAction("Info")
        act_x_rename = menu.addAction("Rename")
        act_x_sep2 = menu.addSeparator()
        act_x_split_join = menu.addAction("Join" if self.m_split else "Split")

        menu.addSeparator()
        act_x_properties = menu.addAction("Properties")

        # Catppuccin quick color preset submenu
        colorMenu = QMenu("Color", menu)
        paletteWidget = QWidget()
        palLayout = QHBoxLayout(paletteWidget)
        palLayout.setContentsMargins(6, 4, 6, 4)
        palLayout.setSpacing(4)

        catppuccin_colors = [
            ("#f38ba8", "Red"),
            ("#fab387", "Peach"),
            ("#f9e2af", "Yellow"),
            ("#a6e3a1", "Green"),
            ("#94e2d5", "Teal"),
            ("#89dceb", "Sky"),
            ("#89b4fa", "Blue"),
            ("#b4befe", "Lavender"),
            ("#cba6f7", "Mauve"),
            ("#f5c2e7", "Pink"),
        ]

        # Reset button
        btn_reset = QPushButton("✕")
        btn_reset.setToolTip("Reset to Default Color")
        btn_reset.setFixedSize(22, 22)
        btn_reset.setStyleSheet("QPushButton { font-weight: bold; color: #888; background: transparent; border: 1px solid #555; border-radius: 3px; } QPushButton:hover { color: #fff; border-color: #888; background: #333; }")
        btn_reset.clicked.connect(lambda: (self.setCustomColor(None), menu.close()))
        palLayout.addWidget(btn_reset)

        for col_hex, col_name in catppuccin_colors:
            btn_col = QPushButton()
            btn_col.setToolTip(col_name)
            btn_col.setFixedSize(22, 22)
            btn_col.setStyleSheet(f"QPushButton {{ background-color: {col_hex}; border: 1px solid rgba(0,0,0,0.4); border-radius: 3px; }} QPushButton:hover {{ border: 2px solid #ffffff; }}")
            btn_col.clicked.connect(lambda checked=False, c=col_hex: (self.setCustomColor(c), menu.close()))
            palLayout.addWidget(btn_col)

        colorWidgetAction = QWidgetAction(colorMenu)
        colorWidgetAction.setDefaultWidget(paletteWidget)
        colorMenu.addAction(colorWidgetAction)
        colorMenu.addSeparator()

        def pickCustomColor():
            menu.close()
            initial = self.m_custom_color if self.m_custom_color else QColor(47, 47, 47)
            chosen = QColorDialog.getColor(initial, None, "Select Node Color")
            if chosen.isValid():
                self.setCustomColor(chosen.name())

        act_custom_color = colorMenu.addAction("Custom Color...")
        act_custom_color.triggered.connect(pickCustomColor)

        act_reset_color = colorMenu.addAction("Reset Color")
        act_reset_color.triggered.connect(lambda: (self.setCustomColor(None), menu.close()))

        menu.addMenu(colorMenu)

        arrangeMenu = QMenu("Arrange & Align", menu)
        act_arr_connected_both = arrangeMenu.addAction("Arrange Connected (Both)")
        act_arr_connected_before = arrangeMenu.addAction("Arrange Connected (Before)")
        act_arr_connected_after = arrangeMenu.addAction("Arrange Connected (After)")
        arrangeMenu.addSeparator()
        act_align_h = arrangeMenu.addAction("Align Horizontally")
        act_align_v = arrangeMenu.addAction("Align Vertically")
        act_dist_h = arrangeMenu.addAction("Distribute Horizontally")
        act_dist_v = arrangeMenu.addAction("Distribute Vertically")
        arrangeMenu.addSeparator()
        act_repel_selected = arrangeMenu.addAction("Auto-Repel (Selected)")
        act_repel_all = arrangeMenu.addAction("Auto-Repel (All)")
        arrangeMenu.addSeparator()
        act_move_aside = arrangeMenu.addAction("Move Aside Non-Connected Nodes")
        act_x_arrange = arrangeMenu.addAction("Auto-arrange All")
        menu.addMenu(arrangeMenu)

        containerMenu = QMenu("Container / Group", menu)
        act_group_vbox = containerMenu.addAction("Group into VBox")
        act_group_hbox = containerMenu.addAction("Group into HBox")
        act_group_grid = containerMenu.addAction("Group into Grid")
        act_group_freeform = containerMenu.addAction("Group into Freeform")
        containerMenu.addSeparator()
        act_ungroup = containerMenu.addAction("Ungroup Container")

        from .patchcanvas import createContainerFromSelected, ungroupNode
        act_group_vbox.triggered.connect(lambda: createContainerFromSelected("vbox"))
        act_group_hbox.triggered.connect(lambda: createContainerFromSelected("hbox"))
        act_group_grid.triggered.connect(lambda: createContainerFromSelected("grid"))
        act_group_freeform.triggered.connect(lambda: createContainerFromSelected("freeform"))
        act_ungroup.triggered.connect(lambda: ungroupNode(self))

        if not getattr(self, "_canvas_container", None):
            act_ungroup.setEnabled(False)

        menu.addMenu(containerMenu)

        selectMenu = QMenu("Select", menu)
        act_sel_all = selectMenu.addAction("Select All\tCtrl+A")
        act_desel = selectMenu.addAction("Deselect\tCtrl+D")
        act_inv = selectMenu.addAction("Invert Selection\tCtrl+Shift+I")
        selectMenu.addSeparator()

        my_type = self.getNodeBadgeType()
        act_sel_same_type = selectMenu.addAction(f"Select All of Same Type ({my_type})")

        from .patchcanvas import getAvailableNodeTypes, selectNodesByType
        byTypeMenu = QMenu("By Type", selectMenu)
        type_actions = []
        for t_name in getAvailableNodeTypes():
            act_t = byTypeMenu.addAction(t_name)
            act_t.triggered.connect(lambda checked=False, t=t_name: selectNodesByType(t))
            type_actions.append(act_t)
        selectMenu.addMenu(byTypeMenu)

        menu.addMenu(selectMenu)

        num_selected = len(canvas.scene.selectedItems()) if canvas.scene else 0
        if num_selected < 2:
            act_align_h.setEnabled(False)
            act_align_v.setEnabled(False)
            act_dist_h.setEnabled(False)
            act_dist_v.setEnabled(False)

        if not features.group_info:
            act_x_info.setVisible(False)

        if not features.group_rename:
            act_x_rename.setVisible(False)

        if not (features.group_info and features.group_rename):
            act_x_sep1.setVisible(False)

        if self.m_plugin_id >= 0 and self.m_plugin_id <= MAX_PLUGIN_ID_ALLOWED:
            menu.addSeparator()
            act_p_jump_rack = menu.addAction("Jump to Rack")
            act_p_edit = menu.addAction("Edit")
            act_p_ui = menu.addAction("Show Custom UI")
            menu.addSeparator()
            act_p_clone = menu.addAction("Clone")
            act_p_rename = menu.addAction("Rename...")
            act_p_replace = menu.addAction("Replace...")
            act_p_remove = menu.addAction("Remove")

            if not self.m_plugin_ui:
                act_p_ui.setVisible(False)

        else:
            act_p_jump_rack = None
            act_p_edit = act_p_ui = None
            act_p_clone = act_p_rename = None
            act_p_replace = act_p_remove = None

        haveIns = haveOuts = False
        for port in canvas.port_list:
            if (
                port.group_id == self.m_group_id
                and port.port_id in self.m_port_list_ids
            ):
                if port.port_mode == PORT_MODE_INPUT:
                    haveIns = True
                elif port.port_mode == PORT_MODE_OUTPUT:
                    haveOuts = True

        if not (self.m_split or bool(haveIns and haveOuts)):
            act_x_sep2.setVisible(False)
            act_x_split_join.setVisible(False)

        act_selected = menu.exec_(event.screenPos())

        if act_selected is None:
            pass

        elif act_selected == act_x_properties:
            self.showPropertiesDialog()

        elif act_selected == act_arr_connected_both:
            from .patchcanvas import arrangeConnected
            arrangeConnected(self, "both")

        elif act_selected == act_arr_connected_before:
            from .patchcanvas import arrangeConnected
            arrangeConnected(self, "before")

        elif act_selected == act_arr_connected_after:
            from .patchcanvas import arrangeConnected
            arrangeConnected(self, "after")

        elif act_selected == act_align_h:
            from .patchcanvas import alignSelected
            alignSelected("horizontal")

        elif act_selected == act_align_v:
            from .patchcanvas import alignSelected
            alignSelected("vertical")

        elif act_selected == act_dist_h:
            from .patchcanvas import alignSelected
            alignSelected("distribute_h")

        elif act_selected == act_dist_v:
            from .patchcanvas import alignSelected
            alignSelected("distribute_v")

        elif act_selected == act_repel_selected:
            from .patchcanvas import repelNodes, getSelectedNodes
            selected = getSelectedNodes()
            repelNodes(selected if len(selected) >= 2 else None)

        elif act_selected == act_repel_all:
            from .patchcanvas import repelNodes
            all_n = []
            for g in canvas.group_list:
                for w in g.widgets:
                    if w is not None and w.isVisible():
                        all_n.append(w)
            repelNodes(all_n)

        elif act_selected == act_move_aside:
            from .patchcanvas import moveAsideNonConnectedNodes
            moveAsideNonConnectedNodes(self)

        elif act_selected == act_sel_all:
            from .patchcanvas import selectAllNodes
            selectAllNodes()

        elif act_selected == act_desel:
            from .patchcanvas import deselectAllNodes
            deselectAllNodes()

        elif act_selected == act_inv:
            from .patchcanvas import invertNodeSelection
            invertNodeSelection()

        elif act_selected == act_sel_same_type:
            from .patchcanvas import selectNodesByType
            selectNodesByType(my_type)

        elif act_selected == act_x_arrange:
            from .patchcanvas import arrange
            arrange()

        elif act_selected == act_x_disc_all:
            for conn_id in conn_list_ids:
                canvas.callback(ACTION_PORTS_DISCONNECT, conn_id, 0, "")

        elif act_selected == act_x_info:
            canvas.callback(ACTION_GROUP_INFO, self.m_group_id, 0, "")

        elif act_selected == act_x_rename:
            canvas.callback(ACTION_GROUP_RENAME, self.m_group_id, 0, "")

        elif act_selected == act_x_split_join:
            if self.m_split:
                canvas.callback(ACTION_GROUP_JOIN, self.m_group_id, 0, "")
            else:
                canvas.callback(ACTION_GROUP_SPLIT, self.m_group_id, 0, "")

        elif act_selected == act_p_jump_rack:
            try:
                from carla_shared import gCarla
                if hasattr(gCarla.gui, "ui"):
                    split_idx = gCarla.gui.ui.tabWidget.indexOf(getattr(gCarla.gui, "tabSplit", None))
                    if split_idx >= 0:
                        gCarla.gui.ui.tabWidget.setCurrentIndex(split_idx)
                    else:
                        gCarla.gui.ui.tabWidget.setCurrentIndex(0)
                    pitem = gCarla.gui.getPluginItem(self.m_plugin_id)
                    if pitem is not None and gCarla.gui.ui.listWidget is not None:
                        gCarla.gui.ui.listWidget.setCurrentItem(pitem)
                        gCarla.gui.ui.listWidget.scrollToItem(pitem)
            except Exception as e:
                print("Error jumping to rack:", e)

        elif act_selected == act_p_edit:
            canvas.callback(ACTION_PLUGIN_EDIT, self.m_plugin_id, 0, "")

        elif act_selected == act_p_ui:
            canvas.callback(ACTION_PLUGIN_SHOW_UI, self.m_plugin_id, 0, "")

        elif act_selected == act_p_clone:
            canvas.callback(ACTION_PLUGIN_CLONE, self.m_plugin_id, 0, "")

        elif act_selected == act_p_rename:
            canvas.callback(ACTION_PLUGIN_RENAME, self.m_plugin_id, 0, "")

        elif act_selected == act_p_replace:
            canvas.callback(ACTION_PLUGIN_REPLACE, self.m_plugin_id, 0, "")

        elif act_selected == act_p_remove:
            canvas.callback(ACTION_PLUGIN_REMOVE, self.m_plugin_id, 0, "")

    def keyPressEvent(self, event):
        if self.m_plugin_id >= 0 and event.key() == Qt.Key_Delete:
            event.accept()
            canvas.callback(ACTION_PLUGIN_REMOVE, self.m_plugin_id, 0, "")
            return
        QGraphicsObject.keyPressEvent(self, event)

    def hoverEnterEvent(self, event):
        if options.auto_select_items:
            if len(canvas.scene.selectedItems()) > 0:
                canvas.scene.clearSelection()
            self.setSelected(True)
        QGraphicsObject.hoverEnterEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if self.m_plugin_id >= 0:
            event.accept()
            canvas.callback(
                ACTION_PLUGIN_SHOW_UI if self.m_plugin_ui else ACTION_PLUGIN_EDIT,
                self.m_plugin_id,
                0,
                "",
            )
            return

        QGraphicsObject.mouseDoubleClickEvent(self, event)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MiddleButton
            or event.source() == Qt.MouseEventSynthesizedByApplication
        ):
            event.ignore()
            return

        canvas.last_z_value += 1
        self.setZValue(canvas.last_z_value)
        ctrlDown = bool(event.modifiers() & Qt.ControlModifier)

        if event.button() == Qt.RightButton:
            event.accept()
            if not self.isSelected():
                canvas.scene.clearSelection()
                self.setSelected(True)
            self.m_mouse_down = False
            return

        elif event.button() == Qt.LeftButton:
            pos = event.pos()
            # Check click on toolbar buttons (Power, Bypass, Jump)
            if self.m_plugin_id >= 0 and hasattr(self, "m_toolbar_buttons"):
                for btn in self.m_toolbar_buttons:
                    rect = btn.get("rect")
                    if rect and rect.contains(pos):
                        event.accept()
                        self.m_mouse_down = False
                        if btn.get("state") == "disabled":
                            return
                        btn_id = btn.get("id")
                        self.m_pressed_btn_id = btn_id
                        self.update()
                        try:
                            from carla_shared import gCarla
                            from carla_backend import PARAMETER_ACTIVE, PARAMETER_DRYWET
                            pitem = gCarla.gui.getPluginItem(self.m_plugin_id) if hasattr(gCarla.gui, "getPluginItem") else None
                            pwidget = pitem.getWidget() if (pitem and hasattr(pitem, "getWidget")) else None

                            if btn_id == "jump":
                                if hasattr(gCarla.gui, "ui"):
                                    split_idx = gCarla.gui.ui.tabWidget.indexOf(getattr(gCarla.gui, "tabSplit", None))
                                    if split_idx >= 0:
                                        gCarla.gui.ui.tabWidget.setCurrentIndex(split_idx)
                                    else:
                                        gCarla.gui.ui.tabWidget.setCurrentIndex(0)
                                    if pitem is not None and gCarla.gui.ui.listWidget is not None:
                                        gCarla.gui.ui.listWidget.setCurrentItem(pitem)
                                        gCarla.gui.ui.listWidget.scrollToItem(pitem)
                            elif btn_id == "power":
                                # Determine current active status reliably
                                if pwidget is not None and hasattr(pwidget, "fIsActive"):
                                    cur = bool(pwidget.fIsActive)
                                elif hasattr(gCarla.gui, "host") and hasattr(gCarla.gui.host, "get_internal_parameter_value"):
                                    cur = bool(gCarla.gui.host.get_internal_parameter_value(self.m_plugin_id, PARAMETER_ACTIVE) >= 0.5)
                                else:
                                    cur = True
                                new_state = not cur

                                gCarla.gui.host.set_active(self.m_plugin_id, new_state)
                                if pwidget is not None:
                                    pwidget.setActive(new_state, sendCallback=True, sendHost=False)

                                self.update()
                                if hasattr(self, "scene") and self.scene():
                                    self.scene().update()
                            elif btn_id == "bypass":
                                cur_val = gCarla.gui.host.get_internal_parameter_value(self.m_plugin_id, PARAMETER_DRYWET)
                                new_val = 1.0 if cur_val == 0.0 else 0.0
                                gCarla.gui.host.set_drywet(self.m_plugin_id, new_val)
                                if pwidget is not None:
                                    pwidget.setParameterValue(PARAMETER_DRYWET, new_val, True)
                                    if hasattr(pwidget, "_update_bypass_state"):
                                        pwidget._update_bypass_state(bool(new_val == 0.0))
                                self.update()
                            elif btn_id == "hide_ports":
                                self.m_hide_unconnected_ports = not getattr(self, "m_hide_unconnected_ports", False)
                                self.updatePositions()
                                if hasattr(self, "scene") and self.scene():
                                    self.scene().update()
                        except Exception as e:
                            print(f"Error handling toolbar button {btn_id}:", e)
                        return

            if ctrlDown:
                event.accept()
                self.setSelected(not self.isSelected())
                self.m_mouse_down = False
                return

            if self.sceneBoundingRect().contains(event.scenePos()):
                self.m_mouse_down = True
                # Drop the expensive box shadows for the duration of the drag
                canvas.dragging = True
            else:
                self.m_mouse_down = False
                event.ignore()
                return

        else:
            self.m_mouse_down = False

        QGraphicsObject.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.m_mouse_down:
            if not self.m_cursor_moving:
                self.setCursor(QCursor(Qt.SizeAllCursor))
                self.m_cursor_moving = True
            self.repaintLines()

            if getattr(canvas, "container_list", None):
                sp = event.scenePos()
                hovered = None
                for c in canvas.container_list:
                    if c.sceneBoundingRect().contains(sp):
                        hovered = c
                        break
                for c in canvas.container_list:
                    if c is hovered:
                        c.setHoverPreview(self, sp)
                    else:
                        c.clearHoverPreview()
        QGraphicsObject.mouseMoveEvent(self, event)

    def hoverMoveEvent(self, event):
        pos = event.pos()
        matched_tip = None
        hover_btn = None
        if self.m_plugin_id >= 0 and hasattr(self, "m_toolbar_buttons"):
            for btn in self.m_toolbar_buttons:
                rect = btn.get("rect")
                if rect and rect.contains(pos):
                    matched_tip = btn.get("tip")
                    hover_btn = btn.get("id")
                    break

        if hover_btn != self.m_hover_btn_id:
            self.m_hover_btn_id = hover_btn
            self.update()

        if matched_tip:
            self.setToolTip(matched_tip)
        else:
            self.setToolTip(self.m_group_name)
        QGraphicsObject.hoverMoveEvent(self, event)

    def hoverLeaveEvent(self, event):
        if self.m_hover_btn_id is not None or self.m_pressed_btn_id is not None:
            self.m_hover_btn_id = None
            self.m_pressed_btn_id = None
            self.update()
        self.setToolTip(self.m_group_name)
        QGraphicsObject.hoverLeaveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.m_pressed_btn_id is not None:
            self.m_pressed_btn_id = None
            self.update()
        moved = self.m_cursor_moving
        if moved:
            self.unsetCursor()
            QTimer.singleShot(0, self.fixPos)

            # Container drop or extraction handling
            if getattr(canvas, "container_list", None):
                sp = event.scenePos()
                dropped_c = None
                for c in canvas.container_list:
                    if c.sceneBoundingRect().contains(sp):
                        dropped_c = c
                        break

                for c in canvas.container_list:
                    c.clearHoverPreview()

                current_c = getattr(self, "_canvas_container", None)
                if dropped_c is not None:
                    if dropped_c.m_layout_mode == "freeform":
                        if current_c and current_c is not dropped_c:
                            current_c.removeItem(self)
                        # Relative offset from container origin
                        rel_x = self.x() - dropped_c.x()
                        rel_y = self.y() - dropped_c.y()
                        dropped_c.addFreeformItem(self, rel_x, rel_y)
                    else:
                        idx = dropped_c.calculateInsertionIndex(sp)
                        if current_c and current_c is not dropped_c:
                            current_c.removeItem(self)
                        dropped_c.addItem(self, idx)
                elif current_c is not None:
                    # Node dragged completely outside container bounds -> detach
                    current_c.removeItem(self)

        self.m_mouse_down = False
        self.m_cursor_moving = False
        canvas.dragging = False
        if moved:
            # Flush the final position now that the drag is over.
            self.slot_signalPositionChangedLater()
        QGraphicsObject.mouseReleaseEvent(self, event)

    def fixPos(self):
        # Do not snap if constrained by a layout container
        if getattr(self, "_canvas_container", None) is not None:
            return

        self.blockSignals(True)
        if getattr(options, "snap_enabled", True):
            gs = max(1, getattr(options, "grid_size", 20))
            self.setX(round(self.x() / gs) * gs)
            self.setY(round(self.y() / gs) * gs)
        else:
            self.setX(round(self.x()))
            self.setY(round(self.y()))
        self.blockSignals(False)

    def boundingRect(self):
        return QRectF(0, 0, self.p_width, self.p_height)

    def shape(self):
        path = QPainterPath()
        radius = options.node_radius if getattr(options, "rounded_nodes", False) else 0
        if radius > 0:
            path.addRoundedRect(
                QRectF(0, 0, self.p_width, self.p_height), radius, radius
            )
        else:
            path.addRect(QRectF(0, 0, self.p_width, self.p_height))
        return path

    def updateTheme(self):
        self.m_font_name = getSystemFont(
            canvas.theme.box_font_size, canvas.theme.box_font_state
        )
        self.m_font_port = getSystemFont(
            canvas.theme.port_font_size, canvas.theme.port_font_state
        )
        if self.shadow is not None:
            self.shadow.setColor(canvas.theme.box_shadow)
        self.update()

    def paint(self, painter, option, widget):
        painter.save()
        radius = options.node_radius if getattr(options, "rounded_nodes", False) else 0
        painter.setRenderHint(
            QPainter.Antialiasing,
            bool(options.antialiasing == ANTIALIASING_FULL or radius > 0),
        )
        rect = QRectF(0, 0, self.p_width, self.p_height)

        # Draw rectangle
        scale = canvas.scene.getScaleFactor() if hasattr(canvas.scene, "getScaleFactor") else 1.0

        # Signal / event flow activity: light up the node while it processes audio
        activity = 0.0
        try:
            from . import signalflow
            if signalflow.state.enabled:
                activity = signalflow.state.levels.get(self.getGroupId(), 0.0)
        except Exception:
            activity = 0.0

        if getattr(self, "m_search_highlight", 0) == 2:
            pen = QPen(QColor(137, 180, 250), max(3.0, 3.0 / scale))
        elif getattr(self, "m_search_highlight", 0) == 1:
            pen = QPen(QColor(116, 199, 236), max(2.0, 2.0 / scale))
        elif self.isSelected():
            pen = QPen(canvas.theme.box_pen_sel)
            pen.setWidthF(max(2.5, 2.5 / scale))
        else:
            pen = QPen(canvas.theme.box_pen)
            pen.setWidthF(pen.widthF() + 0.00001)

        if activity > 0.03 and not getattr(self, "m_search_highlight", 0):
            base = pen.color()
            glow = QColor(150, 230, 255)
            mix = min(1.0, 0.35 + 0.65 * activity)
            pen = QPen(QColor(
                int(base.red() * (1.0 - mix) + glow.red() * mix),
                int(base.green() * (1.0 - mix) + glow.green() * mix),
                int(base.blue() * (1.0 - mix) + glow.blue() * mix),
            ))
            pen.setWidthF(max(2.5, (1.5 + 2.5 * activity) / scale))

        painter.setPen(pen)
        lineHinting = pen.widthF() / 2

        if self.m_custom_color:
            # Match rack custom color tinting logic: blend 15% custom tint with theme background
            c = self.m_custom_color
            bg1 = canvas.theme.box_bg_1
            tinted_bg = QColor(
                int(0.85 * bg1.red() + 0.15 * c.red()),
                int(0.85 * bg1.green() + 0.15 * c.green()),
                int(0.85 * bg1.blue() + 0.15 * c.blue()),
            )
            painter.setBrush(tinted_bg)
        elif canvas.theme.box_bg_type == Theme.THEME_BG_GRADIENT:
            box_gradient = QLinearGradient(0, 0, 0, self.p_height)
            box_gradient.setColorAt(0, canvas.theme.box_bg_1)
            box_gradient.setColorAt(1, canvas.theme.box_bg_2)
            painter.setBrush(box_gradient)
        else:
            painter.setBrush(canvas.theme.box_bg_1)

        rect.adjust(lineHinting, lineHinting, -lineHinting, -lineHinting)
        if radius > 0:
            painter.drawRoundedRect(rect, radius, radius)
        else:
            painter.drawRect(rect)

        # Loudness glow: light up the whole node body while it is processing audio
        if activity > 0.03:
            glow_alpha = int(min(100.0, 25.0 + 90.0 * activity))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(140, 210, 255, glow_alpha))
            if radius > 0:
                painter.drawRoundedRect(rect, radius, radius)
            else:
                painter.drawRect(rect)

        # Draw plugin inline display if supported
        self.paintInlineDisplay(painter)

        # Draw header
        header_height = canvas.theme.box_header_height
        if header_height > 0:
            header_rect = QRectF(
                lineHinting, lineHinting, self.p_width - 2 * lineHinting, header_height
            )
            painter.save()
            if radius > 0:
                header_clip = QPainterPath()
                header_clip.addRoundedRect(rect, radius, radius)
                clipOp = (
                    Qt.ClipOperation.IntersectClip
                    if hasattr(Qt, "ClipOperation")
                    else Qt.IntersectClip
                )
                painter.setClipPath(header_clip, clipOp)

            if canvas.theme.box_header_pixmap:
                painter.setPen(Qt.NoPen)
                painter.setBrush(canvas.theme.box_bg_2)
                painter.drawRect(header_rect)
                painter.drawTiledPixmap(
                    header_rect, canvas.theme.box_header_pixmap, header_rect.topLeft()
                )
            else:
                if self.m_custom_color:
                    # Tint header cleanly: blend 35% custom color with 65% base header background
                    base_h = canvas.theme.box_bg_2 if canvas.theme.box_bg_2 else QColor(36, 39, 58)
                    c = self.m_custom_color
                    header_bg = QColor(
                        int(0.65 * base_h.red() + 0.35 * c.red()),
                        int(0.65 * base_h.green() + 0.35 * c.green()),
                        int(0.65 * base_h.blue() + 0.35 * c.blue()),
                    )
                else:
                    header_bg = canvas.theme.box_bg_2

                if header_bg:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(header_bg)
                    painter.drawRect(header_rect)

                    # Accent line at bottom of header using custom color if available
                    accent_col = self.m_custom_color if self.m_custom_color else canvas.theme.box_pen.color()
                    accent_pen = QPen(accent_col)
                    accent_pen.setWidthF(1.5)
                    painter.setPen(accent_pen)
                    painter.drawLine(
                        QPointF(header_rect.left(), header_rect.bottom()),
                        QPointF(header_rect.right(), header_rect.bottom()),
                    )

            painter.restore()

        # Draw text (Truncated with Ellipsis)
        painter.setFont(self.m_font_name)

        if self.m_custom_color:
            # High-contrast readable title text against tinted header
            base_h = canvas.theme.box_bg_2 if canvas.theme.box_bg_2 else QColor(36, 39, 58)
            c = self.m_custom_color
            lum = (0.299 * (0.65 * base_h.red() + 0.35 * c.red()) +
                   0.587 * (0.65 * base_h.green() + 0.35 * c.green()) +
                   0.114 * (0.65 * base_h.blue() + 0.35 * c.blue()))
            text_color = QColor(20, 20, 20) if lum > 145 else QColor(245, 245, 250)
            painter.setPen(QPen(text_color))
        elif self.isSelected():
            painter.setPen(canvas.theme.box_text_sel if canvas.theme.box_text_sel else canvas.theme.box_text)
        else:
            painter.setPen(canvas.theme.box_text)

        metrics = QFontMetrics(self.m_font_name)
        elide_mode = (
            Qt.TextElideMode.ElideRight
            if hasattr(Qt, "TextElideMode")
            else Qt.ElideRight
        )

        # Calculate available width with safer padding
        if canvas.theme.box_use_icon:
            available_width = self.p_width - 35  # Account for icon width + padding
            textPos = QPointF(25, canvas.theme.box_text_ypos)
        else:
            available_width = self.p_width - 20  # 10px padding on each side

        # Truncate string gracefully based on available pixel width
        badge_info = None
        badge_w = 0
        if self.m_plugin_id >= 0:
            try:
                from carla_shared import gCarla
                from carla_skin import CATEGORY_BADGES
                pinfo = gCarla.gui.host.get_plugin_info(self.m_plugin_id)
                cat = pinfo.get("category", 0)
                if cat in CATEGORY_BADGES:
                    badge_info = CATEGORY_BADGES[cat]
                else:
                    # Fallback for plugins with category NONE/0
                    hints = pinfo.get("hints", 0)
                    from carla_backend import PLUGIN_IS_SYNTH
                    if hints & PLUGIN_IS_SYNTH:
                        badge_info = ("SYNTH", "#f38ba8")
                    else:
                        badge_info = ("PLUGIN", "#89b4fa")
            except Exception:
                badge_info = ("PLUGIN", "#89b4fa")
        else:
            # Determine badge for sinks, sources, hardware, apps, and split I/O
            has_ins = False
            has_outs = False
            pid_set = set(self.m_port_list_ids)
            for port in canvas.port_list:
                if port.port_id in pid_set:
                    if getattr(port, "port_mode", None) == PORT_MODE_INPUT:
                        has_ins = True
                    elif getattr(port, "port_mode", None) == PORT_MODE_OUTPUT:
                        has_outs = True

            low_name = self.m_group_name.lower()
            if self.m_split_mode == PORT_MODE_INPUT or (has_ins and not has_outs):
                if any(k in low_name for k in ("sink", "playback", "speaker", "headphone")):
                    badge_info = ("SINK", "#a6e3a1")  # Green
                else:
                    badge_info = ("IN", "#89dceb")    # Sky
            elif self.m_split_mode == PORT_MODE_OUTPUT or (has_outs and not has_ins):
                if any(k in low_name for k in ("source", "capture", "mic")):
                    badge_info = ("SOURCE", "#fab387")  # Peach
                else:
                    badge_info = ("OUT", "#f9e2af")     # Yellow
            elif getattr(self, "m_icon", None) == 1 or any(k in low_name for k in ("system", "hardware", "alsa", "hw:")):
                badge_info = ("HW", "#b4befe")          # Lavender
            elif has_ins and has_outs:
                badge_info = ("APP", "#cba6f7")         # Mauve
            else:
                badge_info = ("NODE", "#6c7086")        # Slate

        # Check if plugin actually supports active/bypass
        has_rack_pair = self.m_plugin_id >= 0
        is_active = True
        btn_size = 12

        if has_rack_pair:
            try:
                from carla_shared import gCarla
                pitem = gCarla.gui.getPluginItem(self.m_plugin_id) if hasattr(gCarla.gui, "getPluginItem") else None
                pwidget = pitem.getWidget() if (pitem and hasattr(pitem, "getWidget")) else None
                if pwidget is not None and hasattr(pwidget, "fIsActive"):
                    is_active = bool(pwidget.fIsActive)
                elif hasattr(gCarla.gui, "host") and hasattr(gCarla.gui.host, "get_internal_parameter_value"):
                    from carla_backend import PARAMETER_ACTIVE
                    val = gCarla.gui.host.get_internal_parameter_value(self.m_plugin_id, PARAMETER_ACTIVE)
                    is_active = bool(val >= 0.5)
            except Exception:
                is_active = True

        if badge_info:
            b_text = badge_info[0]
            badge_w = max(26, len(b_text) * 6 + 8)
            available_width = max(10, available_width - badge_w - 6)
        else:
            available_width = max(10, available_width - 6)

        elided_name = metrics.elidedText(
            self.m_group_name, elide_mode, int(max(0, available_width))
        )

        if not canvas.theme.box_use_icon:
            drawn_name_size = fontHorizontalAdvance(self.m_font_name, elided_name)
            rem = self.p_width - drawn_name_size - (badge_w + 4 if badge_info else 0)
            textPos = QPointF(max(8, rem / 2), canvas.theme.box_text_ypos)
        else:
            textPos = QPointF(25, canvas.theme.box_text_ypos)

        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.drawText(QPointF(round(textPos.x()), round(textPos.y())), elided_name)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Right-aligned Category badge pill in top header line
        if badge_info:
            b_text, b_col_hex = badge_info
            b_col = QColor(b_col_hex)
            b_h = 12
            b_y = int(lineHinting + (header_height - b_h) / 2) if header_height > 0 else int(lineHinting + 2)
            b_x = int(self.p_width - 6 - badge_w)
            b_rect = QRectF(b_x, b_y, badge_w, b_h)

            painter.save()
            painter.setPen(Qt.NoPen)
            # Muted semantic translucent badge
            pill_bg = QColor(b_col.red(), b_col.green(), b_col.blue(), 40)
            painter.setBrush(pill_bg)
            painter.drawRoundedRect(b_rect, 2.5, 2.5)

            painter.setPen(QPen(b_col, 0.8))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(b_rect, 2.5, 2.5)

            b_font = QFont(self.m_font_name)
            b_font.setPointSize(max(6, b_font.pointSize() - 4))
            b_font.setBold(True)
            painter.setFont(b_font)
            painter.setPen(b_col)
            painter.drawText(b_rect, Qt.AlignCenter, b_text)
            painter.restore()

        # Line 2: Centered Button Toolbar for rack paired nodes
        self.m_toolbar_buttons = []

        if has_rack_pair and header_height > 0:
            subbar_y = header_height
            subbar_h = 22

            # Sub-bar background strip with subtle separator
            subbar_rect = QRectF(lineHinting, subbar_y, self.p_width - 2 * lineHinting, subbar_h)
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 45))
            painter.drawRect(subbar_rect)
            # Subtle bottom separator line
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
            painter.drawLine(QPointF(subbar_rect.left(), subbar_rect.bottom()), QPointF(subbar_rect.right(), subbar_rect.bottom()))
            painter.restore()

            # Inspect states for 3 controls
            # 1. Power State
            power_state = "active" if is_active else "inactive"
            power_tip = "Power: Active (Click to disable DSP processing)" if is_active else "Power: Disabled (Click to enable DSP processing)"

            # 2. Bypass State (Dry/Wet)
            bypass_state = "disabled"
            bypass_tip = "Bypass: Not supported for this plugin"
            try:
                from carla_backend import PLUGIN_CAN_DRYWET, PARAMETER_DRYWET
                from carla_shared import gCarla
                hints = gCarla.gui.host.get_plugin_info(self.m_plugin_id).get("hints", 0) if hasattr(gCarla.gui, "host") else 0
                if bool(hints & PLUGIN_CAN_DRYWET):
                    dw_val = gCarla.gui.host.get_internal_parameter_value(self.m_plugin_id, PARAMETER_DRYWET)
                    if dw_val == 0.0:
                        bypass_state = "active"    # Bypassed
                        bypass_tip = "Bypass: Active (Dry/Wet 0% - Click to activate audio)"
                    else:
                        bypass_state = "inactive"  # Passing through normally
                        bypass_tip = "Bypass: Inactive (Dry/Wet 100% - Click to bypass)"
            except Exception:
                pass

            # 3. Jump to Rack State
            jump_state = "inactive"
            jump_tip = "Jump to Rack View (Focus and view plugin controls in Rack)"

            # 4. Hide Unconnected Ports State
            hide_ports_active = getattr(self, "m_hide_unconnected_ports", False)
            hide_ports_state = "active" if hide_ports_active else "inactive"
            hide_ports_tip = "Hide Unused Ports: Active (Click to show all ports)" if hide_ports_active else "Hide Unused Ports: Inactive (Click to hide unconnected ports)"

            # Button definitions with Nerd Font / FontAwesome icons
            # Power: ⏻ (\uf011), Bypass: ⊘ (\uf05e), Jump:  (\uf08e), Hide Unconnected Ports: / (\uf066/\uf065)
            btn_defs = [
                {
                    "id": "power",
                    "icon": "\uf011",
                    "state": power_state,
                    "tip": power_tip,
                },
                {
                    "id": "bypass",
                    "icon": "\uf05e",
                    "state": bypass_state,
                    "tip": bypass_tip,
                },
                {
                    "id": "hide_ports",
                    "icon": "\uf066" if hide_ports_active else "\uf065",
                    "state": hide_ports_state,
                    "tip": hide_ports_tip,
                },
                {
                    "id": "jump",
                    "icon": "\uf08e",
                    "state": jump_state,
                    "tip": jump_tip,
                },
            ]

            # Uniform fixed square buttons
            btn_size = 18.0
            btn_spacing = 6.0
            total_btns_w = len(btn_defs) * btn_size + (len(btn_defs) - 1) * btn_spacing
            start_x = max(6.0, (self.p_width - total_btns_w) / 2.0)
            btn_y = subbar_y + (subbar_h - btn_size) / 2.0

            btn_font = QFont(self.m_font_name)
            btn_font.setPointSize(max(9, btn_font.pointSize()))
            btn_font.setBold(True)
            painter.save()
            painter.setFont(btn_font)

            cur_x = start_x

            for b in btn_defs:
                b_rect = QRectF(cur_x, btn_y, btn_size, btn_size)
                b["rect"] = b_rect
                self.m_toolbar_buttons.append(b)

                btn_id = b["id"]
                st = b["state"]
                is_hovered = (getattr(self, "m_hover_btn_id", None) == btn_id and st != "disabled")
                is_pressed = (getattr(self, "m_pressed_btn_id", None) == btn_id and st != "disabled")

                if st == "disabled":
                    btn_bg = QColor(255, 255, 255, 4)
                    icon_pen = QColor(140, 145, 160, 60)
                elif is_pressed:
                    btn_bg = QColor(255, 255, 255, 55)
                    icon_pen = QColor(255, 255, 255, 255)
                elif is_hovered:
                    btn_bg = QColor(255, 255, 255, 28)
                    icon_pen = QColor(250, 250, 255, 250)
                elif st == "active":
                    if btn_id == "power":
                        btn_bg = QColor(137, 180, 250, 35)
                        icon_pen = QColor(137, 180, 250, 255)
                    elif btn_id == "bypass":
                        btn_bg = QColor(250, 179, 135, 35)
                        icon_pen = QColor(250, 179, 135, 255)
                    else:
                        btn_bg = QColor(255, 255, 255, 18)
                        icon_pen = QColor(230, 235, 245, 240)
                else: # inactive
                    btn_bg = QColor(255, 255, 255, 10)
                    icon_pen = QColor(180, 185, 200, 170)

                painter.setPen(Qt.NoPen)
                painter.setBrush(btn_bg)
                painter.drawRoundedRect(b_rect, 3.0, 3.0)

                draw_rect = b_rect.translated(0, 0.8) if is_pressed else b_rect
                painter.setPen(icon_pen)
                # Fallback to standard unicode icon if nerd font glyph not present
                try:
                    painter.drawText(draw_rect, Qt.AlignCenter, b["icon"])
                except Exception:
                    pass

                cur_x += btn_size + btn_spacing

            painter.restore()

        painter.restore()

    def paintInlineDisplay(self, painter):
        if self.m_plugin_inline == self.INLINE_DISPLAY_DISABLED:
            return
        if not options.inline_displays:
            return

        subbar_h = 22 if self.m_plugin_id >= 0 else 0
        header_total_h = canvas.theme.box_header_height + subbar_h
        inwidth = self.p_width - 16 - self.p_width_in - self.p_width_out
        inheight = (
            self.p_height
            - 3
            - header_total_h
            - canvas.theme.box_header_spacing
            - canvas.theme.port_spacing
        )

        scaling = canvas.scene.getScaleFactor() * canvas.scene.getDevicePixelRatioF()

        if (
            self.m_plugin_id >= 0
            and self.m_plugin_id <= MAX_PLUGIN_ID_ALLOWED
            and (
                self.m_plugin_inline == self.INLINE_DISPLAY_ENABLED
                or self.m_inline_scaling != scaling
            )
        ):
            if self.m_inline_first:
                size = "%i:%i" % (int(50 * scaling), int(50 * scaling))
            else:
                size = "%i:%i" % (int(inwidth * scaling), int(inheight * scaling))
            data = canvas.callback(ACTION_INLINE_DISPLAY, self.m_plugin_id, 0, size)
            if data is None:
                return

            img_format = QImage.Format_ARGB32
            self.m_inline_image = QImage(
                data["data"],
                data["width"],
                data["height"],
                data["stride"],
                img_format,
            ).copy()
            self.m_inline_scaling = scaling
            self.m_plugin_inline = self.INLINE_DISPLAY_CACHED

            # make room for inline display, in a square shape
            if self.m_inline_first:
                self.m_inline_first = False
                aspectRatio = data["width"] / data["height"]
                self.p_height = int(max((header_total_h + 50) * scaling, self.p_height))
                self.p_width += int(
                    max(
                        0,
                        min(
                            (80 - 14) * scaling,
                            (inheight - inwidth) * aspectRatio * scaling,
                        ),
                    )
                )
                self.repositionPorts()
                self.repaintLines(True)
                self.update()
                return

        if self.m_inline_image is None:
            print(
                "ERROR: inline display image is None for",
                self.m_plugin_id,
                self.m_group_name,
            )
            return

        swidth = self.m_inline_image.width() / scaling
        sheight = self.m_inline_image.height() / scaling

        srcx = int(
            self.p_width_in
            + (self.p_width - self.p_width_in - self.p_width_out) / 2
            - swidth / 2
        )
        srcy = int(
            header_total_h
            + canvas.theme.box_header_spacing
            + 1
            + max(0, (inheight - sheight) / 2)
        )

        painter.drawImage(QRectF(srcx, srcy, swidth, sheight), self.m_inline_image)

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.ItemPositionHasChanged
            or change == 1
        ):
            self.repaintLines()
            self.slot_signalPositionChangedLater()

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            # A focused/selected node must update its cables right away
            self.updateConnectionSelectionState()

        return super().itemChange(change, value)


# ------------------------------------------------------------------------------------------------------------
