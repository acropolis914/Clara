"""Declarative multi-tab schema and dynamic form builder for Clara Settings.

Provides comprehensive schemas for:
- General (Application & Session, Interface & Theming, Rack Layout)
- Patchbay (Appearance & Styling, Motion, FX & Performance)
- Engine & Audio (Driver & Buffers, Processing & Routing)
- OSC & Remote (Network & Ports)
- Wine & Bridges (Architecture, Realtime Priority)
- Advanced & Experimental (Developer Options, Safety)
"""

from qt_compat import (
    Qt,
    QWidget,
    QLabel,
    QCheckBox,
    QComboBox,
    QSlider,
    QSpinBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
    QFileDialog,
)

from carla_shared import (
    # Main
    CARLA_KEY_MAIN_PROJECT_FOLDER,
    CARLA_DEFAULT_MAIN_PROJECT_FOLDER,
    CARLA_KEY_MAIN_CONFIRM_EXIT,
    CARLA_DEFAULT_MAIN_CONFIRM_EXIT,
    CARLA_KEY_MAIN_MINIMIZE_TO_TRAY,
    CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY,
    CARLA_KEY_MAIN_SHOW_LOGS,
    CARLA_DEFAULT_MAIN_SHOW_LOGS,
    CARLA_KEY_MAIN_LOG_TO_CONSOLE,
    CARLA_DEFAULT_MAIN_LOG_TO_CONSOLE,
    CARLA_KEY_MAIN_AUTOSAVE_ENABLED,
    CARLA_DEFAULT_MAIN_AUTOSAVE_ENABLED,
    CARLA_KEY_MAIN_AUTOSAVE_INTERVAL,
    CARLA_DEFAULT_MAIN_AUTOSAVE_INTERVAL,
    CARLA_KEY_MAIN_AUTOSAVE_MAX,
    CARLA_DEFAULT_MAIN_AUTOSAVE_MAX,
    CARLA_KEY_MAIN_REFRESH_INTERVAL,
    CARLA_DEFAULT_MAIN_REFRESH_INTERVAL,
    CARLA_KEY_MAIN_SYSTEM_ICONS,
    CARLA_DEFAULT_MAIN_SYSTEM_ICONS,
    CARLA_KEY_MAIN_CLASSIC_SKIN,
    CARLA_DEFAULT_MAIN_CLASSIC_SKIN,
    CARLA_KEY_MAIN_USE_SYSTEM_THEME,
    CARLA_DEFAULT_MAIN_USE_SYSTEM_THEME,
    CARLA_KEY_MAIN_APP_THEME,
    CARLA_DEFAULT_MAIN_APP_THEME,
    # Canvas
    CARLA_KEY_CANVAS_SIZE,
    CARLA_DEFAULT_CANVAS_SIZE,
    CARLA_KEY_CANVAS_LINE_STYLE,
    CARLA_DEFAULT_CANVAS_LINE_STYLE,
    CARLA_KEY_CANVAS_LINE_STROKE,
    CARLA_DEFAULT_CANVAS_LINE_STROKE,
    CARLA_KEY_CANVAS_LINE_OPACITY,
    CARLA_DEFAULT_CANVAS_LINE_OPACITY,
    CARLA_KEY_CANVAS_ROUNDED_NODES,
    CARLA_DEFAULT_CANVAS_ROUNDED_NODES,
    CARLA_KEY_CANVAS_NODE_RADIUS,
    CARLA_DEFAULT_CANVAS_NODE_RADIUS,
    CARLA_KEY_CANVAS_NODE_MIN_WIDTH,
    CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH,
    CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS,
    CARLA_DEFAULT_CANVAS_AUTO_HIDE_GROUPS,
    CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS,
    CARLA_DEFAULT_CANVAS_AUTO_SELECT_ITEMS,
    CARLA_KEY_CANVAS_BOX_SHADOWS,
    CARLA_DEFAULT_CANVAS_BOX_SHADOWS,
    CARLA_KEY_CANVAS_SHADOW_OPACITY,
    CARLA_DEFAULT_CANVAS_SHADOW_OPACITY,
    CARLA_KEY_CANVAS_SHADOW_SPREAD,
    CARLA_DEFAULT_CANVAS_SHADOW_SPREAD,
    CARLA_KEY_CANVAS_SHADOW_DISTANCE,
    CARLA_DEFAULT_CANVAS_SHADOW_DISTANCE,
    CARLA_KEY_CANVAS_SHADOW_DRAG,
    CARLA_DEFAULT_CANVAS_SHADOW_DRAG,
    CARLA_KEY_CANVAS_SIGNAL_FLOW,
    CARLA_DEFAULT_CANVAS_SIGNAL_FLOW,
    CARLA_KEY_CANVAS_NODE_TRANSITIONS,
    CARLA_DEFAULT_CANVAS_NODE_TRANSITIONS,
    CARLA_KEY_CANVAS_ANTIALIASING,
    CARLA_DEFAULT_CANVAS_ANTIALIASING,
    CARLA_KEY_CANVAS_HQ_ANTIALIASING,
    CARLA_DEFAULT_CANVAS_HQ_ANTIALIASING,
    CARLA_KEY_CANVAS_INLINE_DISPLAYS,
    CARLA_DEFAULT_CANVAS_INLINE_DISPLAYS,
    CARLA_KEY_CANVAS_EYE_CANDY,
    CARLA_KEY_CANVAS_FANCY_EYE_CANDY,
    CARLA_KEY_CANVAS_USE_BEZIER_LINES,
    # OSC
    CARLA_KEY_OSC_ENABLED,
    CARLA_DEFAULT_OSC_ENABLED,
    CARLA_KEY_OSC_TCP_PORT_ENABLED,
    CARLA_DEFAULT_OSC_TCP_PORT_ENABLED,
    CARLA_KEY_OSC_TCP_PORT_NUMBER,
    CARLA_DEFAULT_OSC_TCP_PORT_NUMBER,
    CARLA_KEY_OSC_TCP_PORT_RANDOM,
    CARLA_DEFAULT_OSC_TCP_PORT_RANDOM,
    CARLA_KEY_OSC_UDP_PORT_ENABLED,
    CARLA_DEFAULT_OSC_UDP_PORT_ENABLED,
    CARLA_KEY_OSC_UDP_PORT_NUMBER,
    CARLA_DEFAULT_OSC_UDP_PORT_NUMBER,
    CARLA_KEY_OSC_UDP_PORT_RANDOM,
    CARLA_DEFAULT_OSC_UDP_PORT_RANDOM,
    # Wine
    CARLA_KEY_WINE_EXECUTABLE,
    CARLA_DEFAULT_WINE_EXECUTABLE,
    CARLA_KEY_WINE_AUTO_PREFIX,
    CARLA_DEFAULT_WINE_AUTO_PREFIX,
    CARLA_KEY_WINE_FALLBACK_PREFIX,
    CARLA_DEFAULT_WINE_FALLBACK_PREFIX,
    CARLA_KEY_WINE_RT_PRIO_ENABLED,
    CARLA_DEFAULT_WINE_RT_PRIO_ENABLED,
    CARLA_KEY_WINE_BASE_RT_PRIO,
    CARLA_DEFAULT_WINE_BASE_RT_PRIO,
    CARLA_KEY_WINE_SERVER_RT_PRIO,
    CARLA_DEFAULT_WINE_SERVER_RT_PRIO,
    # Engine
    CARLA_KEY_ENGINE_PREFER_PLUGIN_BRIDGES,
    CARLA_DEFAULT_PREFER_PLUGIN_BRIDGES,
    # Experimental
    CARLA_KEY_EXPERIMENTAL_JACK_APPS,
    CARLA_DEFAULT_EXPERIMENTAL_JACK_APPS,
    CARLA_KEY_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
    CARLA_DEFAULT_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
    CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES,
    CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES,
)


GENERAL_SCHEMA = {
    "columns": [
        {
            "id": "col_left",
            "groups": [
                {
                    "title": "Application & Session",
                    "fields": [
                        {
                            "id": "project_folder",
                            "type": "path",
                            "label": "Project folder:",
                            "key": CARLA_KEY_MAIN_PROJECT_FOLDER,
                            "default": CARLA_DEFAULT_MAIN_PROJECT_FOLDER,
                        },
                        {
                            "id": "confirm_exit",
                            "type": "checkbox",
                            "label": "Confirm before exit when session has unsaved changes",
                            "key": CARLA_KEY_MAIN_CONFIRM_EXIT,
                            "default": CARLA_DEFAULT_MAIN_CONFIRM_EXIT,
                        },
                        {
                            "id": "minimize_to_tray",
                            "type": "checkbox",
                            "label": "Minimize to system tray instead of taskbar",
                            "key": CARLA_KEY_MAIN_MINIMIZE_TO_TRAY,
                            "default": CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY,
                        },
                        {
                            "id": "show_statusbar",
                            "type": "checkbox",
                            "label": "Show statusbar at bottom",
                            "key": "ShowStatusBar",
                            "default": True,
                        },
                        {
                            "id": "show_logs",
                            "type": "checkbox",
                            "label": "Show application log viewer",
                            "key": CARLA_KEY_MAIN_SHOW_LOGS,
                            "default": CARLA_DEFAULT_MAIN_SHOW_LOGS,
                        },
                        {
                            "id": "log_to_console",
                            "type": "checkbox",
                            "label": "Mirror application logs to terminal (Rich colored)",
                            "key": CARLA_KEY_MAIN_LOG_TO_CONSOLE,
                            "default": CARLA_DEFAULT_MAIN_LOG_TO_CONSOLE,
                        },
                    ],
                },
                {
                    "title": "Automatic Project Backup (Autosave)",
                    "fields": [
                        {
                            "id": "autosave_enabled",
                            "type": "checkbox",
                            "label": "Enable automatic rotating project backup",
                            "key": CARLA_KEY_MAIN_AUTOSAVE_ENABLED,
                            "default": CARLA_DEFAULT_MAIN_AUTOSAVE_ENABLED,
                        },
                        {
                            "id": "autosave_interval",
                            "type": "spinbox",
                            "label": "Autosave interval (minutes):",
                            "key": CARLA_KEY_MAIN_AUTOSAVE_INTERVAL,
                            "default": CARLA_DEFAULT_MAIN_AUTOSAVE_INTERVAL,
                            "min": 1,
                            "max": 120,
                            "depends_on": "autosave_enabled",
                        },
                        {
                            "id": "autosave_max",
                            "type": "spinbox",
                            "label": "Max backups to retain:",
                            "key": CARLA_KEY_MAIN_AUTOSAVE_MAX,
                            "default": CARLA_DEFAULT_MAIN_AUTOSAVE_MAX,
                            "min": 1,
                            "max": 50,
                            "depends_on": "autosave_enabled",
                        },
                    ],
                },
            ],
        },
        {
            "id": "col_right",
            "groups": [
                {
                    "title": "Rack Layout & Spacing",
                    "fields": [
                        {
                            "id": "rack_spacing",
                            "type": "slider",
                            "label": "Slot vertical spacing:",
                            "key": "RackItemSpacing",
                            "default": 4,
                            "min": 0,
                            "max": 16,
                            "suffix": " px",
                        },
                        {
                            "id": "rack_padding",
                            "type": "slider",
                            "label": "Slot internal padding:",
                            "key": "RackItemPadding",
                            "default": 6,
                            "min": 2,
                            "max": 16,
                            "suffix": " px",
                        },
                        {
                            "id": "rack_min_width",
                            "type": "slider",
                            "label": "Slot minimum width:",
                            "key": "RackItemMinWidth",
                            "default": 200,
                            "min": 180,
                            "max": 450,
                            "suffix": " px",
                        },
                    ],
                },
                {
                    "title": "Interface & Theming",
                    "fields": [
                        {
                            "id": "use_system_theme",
                            "type": "checkbox",
                            "label": "Use system desktop theme (native Qt styling)",
                            "key": CARLA_KEY_MAIN_USE_SYSTEM_THEME,
                            "default": CARLA_DEFAULT_MAIN_USE_SYSTEM_THEME,
                        },
                        {
                            "id": "app_theme",
                            "type": "combobox",
                            "label": "Application theme:",
                            "key": CARLA_KEY_MAIN_APP_THEME,
                            "default": CARLA_DEFAULT_MAIN_APP_THEME,
                            "options_factory": "app_themes",
                            "depends_on": "not use_system_theme",
                        },
                        {
                            "id": "classic_skin",
                            "type": "checkbox",
                            "label": "Use classic plugin skin by default",
                            "key": CARLA_KEY_MAIN_CLASSIC_SKIN,
                            "default": CARLA_DEFAULT_MAIN_CLASSIC_SKIN,
                        },
                        {
                            "id": "system_icons",
                            "type": "checkbox",
                            "label": "Use system desktop icons if available",
                            "key": CARLA_KEY_MAIN_SYSTEM_ICONS,
                            "default": CARLA_DEFAULT_MAIN_SYSTEM_ICONS,
                        },
                    ],
                },
                {
                    "title": "Diagnostics & Refresh",
                    "fields": [
                        {
                            "id": "refresh_interval",
                            "type": "spinbox",
                            "label": "UI refresh rate (ms):",
                            "key": CARLA_KEY_MAIN_REFRESH_INTERVAL,
                            "default": CARLA_DEFAULT_MAIN_REFRESH_INTERVAL,
                            "min": 10,
                            "max": 100,
                        },
                    ],
                },
            ],
        },
    ]
}


PATCHBAY_SCHEMA = {
    "columns": [
        {
            "id": "col_left",
            "groups": [
                {
                    "title": "Nodes",
                    "fields": [
                        {
                            "id": "canvas_size",
                            "type": "combobox",
                            "label": "Canvas size:",
                            "key": CARLA_KEY_CANVAS_SIZE,
                            "default": CARLA_DEFAULT_CANVAS_SIZE,
                            "options": [
                                ("1920x1200 (Default)", "1920x1200"),
                                ("2560x1440 (2K)", "2560x1440"),
                                ("3100x2400 (Large)", "3100x2400"),
                                ("3840x2160 (4K)", "3840x2160"),
                                ("5120x2880 (5K)", "5120x2880"),
                            ],
                        },
                        {
                            "id": "rounded_nodes",
                            "type": "checkbox",
                            "label": "Rounded nodes",
                            "key": CARLA_KEY_CANVAS_ROUNDED_NODES,
                            "default": CARLA_DEFAULT_CANVAS_ROUNDED_NODES,
                        },
                        {
                            "id": "node_radius",
                            "type": "slider",
                            "label": "Corner radius:",
                            "key": CARLA_KEY_CANVAS_NODE_RADIUS,
                            "default": CARLA_DEFAULT_CANVAS_NODE_RADIUS,
                            "min": 2,
                            "max": 24,
                            "suffix": " px",
                            "depends_on": "rounded_nodes",
                        },
                        {
                            "id": "node_min_width",
                            "type": "slider",
                            "label": "Min node width:",
                            "key": CARLA_KEY_CANVAS_NODE_MIN_WIDTH,
                            "default": CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH,
                            "min": 100,
                            "max": 320,
                            "suffix": " px",
                        },
                        {
                            "id": "inline_displays",
                            "type": "checkbox",
                            "label": "Embedded inline displays",
                            "tooltip": "Render embedded plugin meters and UI displays directly inside nodes",
                            "key": CARLA_KEY_CANVAS_INLINE_DISPLAYS,
                            "default": CARLA_DEFAULT_CANVAS_INLINE_DISPLAYS,
                        },
                    ],
                },
                {
                    "title": "Cables",
                    "fields": [
                        {
                            "id": "line_style",
                            "type": "combobox",
                            "label": "Cable routing:",
                            "key": CARLA_KEY_CANVAS_LINE_STYLE,
                            "default": CARLA_DEFAULT_CANVAS_LINE_STYLE,
                            "options_factory": "line_styles",
                        },
                        {
                            "id": "line_stroke",
                            "type": "combobox",
                            "label": "Cable pattern:",
                            "key": CARLA_KEY_CANVAS_LINE_STROKE,
                            "default": CARLA_DEFAULT_CANVAS_LINE_STROKE,
                            "options": [
                                ("Solid", "solid"),
                                ("Dotted", "dotted"),
                                ("Dashed", "dashed"),
                            ],
                        },
                        {
                            "id": "line_opacity",
                            "type": "slider",
                            "label": "Cable opacity:",
                            "key": CARLA_KEY_CANVAS_LINE_OPACITY,
                            "default": CARLA_DEFAULT_CANVAS_LINE_OPACITY,
                            "min": 20,
                            "max": 100,
                            "suffix": "%",
                        },
                        {
                            "id": "signal_flow",
                            "type": "checkbox",
                            "label": "Signal flow & cable pulses",
                            "tooltip": "Live audio activity pulse traveling along patchbay cables",
                            "key": CARLA_KEY_CANVAS_SIGNAL_FLOW,
                            "default": CARLA_DEFAULT_CANVAS_SIGNAL_FLOW,
                        },
                    ],
                },
            ],
        },
        {
            "id": "col_right",
            "groups": [
                {
                    "title": "Node shadows",
                    "fields": [
                        {
                            "id": "box_shadows",
                            "type": "checkbox",
                            "label": "Drop shadows",
                            "tooltip": "Render soft drop shadows beneath canvas node boxes",
                            "key": CARLA_KEY_CANVAS_BOX_SHADOWS,
                            "legacy_keys": [CARLA_KEY_CANVAS_EYE_CANDY],
                            "default": CARLA_DEFAULT_CANVAS_BOX_SHADOWS,
                        },
                        {
                            "id": "shadow_spread",
                            "type": "slider",
                            "label": "Spread:",
                            "tooltip": "How far the shadow fades out",
                            "key": CARLA_KEY_CANVAS_SHADOW_SPREAD,
                            "default": CARLA_DEFAULT_CANVAS_SHADOW_SPREAD,
                            "min": 0,
                            "max": 40,
                            "suffix": " px",
                            "depends_on": "box_shadows",
                        },
                        {
                            "id": "shadow_distance",
                            "type": "slider",
                            "label": "Distance:",
                            "tooltip": "How far the shadow is offset from the node",
                            "key": CARLA_KEY_CANVAS_SHADOW_DISTANCE,
                            "default": CARLA_DEFAULT_CANVAS_SHADOW_DISTANCE,
                            "min": 0,
                            "max": 20,
                            "suffix": " px",
                            "depends_on": "box_shadows",
                        },
                        {
                            "id": "shadow_opacity",
                            "type": "slider",
                            "label": "Opacity:",
                            "tooltip": "Shadow strength relative to the theme",
                            "key": CARLA_KEY_CANVAS_SHADOW_OPACITY,
                            "default": CARLA_DEFAULT_CANVAS_SHADOW_OPACITY,
                            "min": 0,
                            "max": 100,
                            "suffix": "%",
                            "depends_on": "box_shadows",
                        },
                        {
                            "id": "shadow_dragging",
                            "type": "checkbox",
                            "label": "Keep shadows while dragging nodes",
                            "tooltip": "Shadows stay visible while a node is dragged; costs some frames on large racks",
                            "key": CARLA_KEY_CANVAS_SHADOW_DRAG,
                            "default": CARLA_DEFAULT_CANVAS_SHADOW_DRAG,
                            "depends_on": "box_shadows",
                        },
                    ],
                },
                {
                    "title": "Rendering",
                    "fields": [
                        {
                            "id": "auto_hide_groups",
                            "type": "checkbox",
                            "label": "Auto-hide empty groups",
                            "key": CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS,
                            "default": CARLA_DEFAULT_CANVAS_AUTO_HIDE_GROUPS,
                        },
                        {
                            "id": "auto_select",
                            "type": "checkbox",
                            "label": "Auto-select items on hover",
                            "key": CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS,
                            "default": CARLA_DEFAULT_CANVAS_AUTO_SELECT_ITEMS,
                        },
                        {
                            "id": "node_transitions",
                            "type": "checkbox",
                            "label": "Smooth node transitions",
                            "tooltip": "Animated fade-in and scale effects when nodes appear or disappear",
                            "key": CARLA_KEY_CANVAS_NODE_TRANSITIONS,
                            "legacy_keys": [CARLA_KEY_CANVAS_FANCY_EYE_CANDY],
                            "default": CARLA_DEFAULT_CANVAS_NODE_TRANSITIONS,
                        },
                        {
                            "id": "antialiasing",
                            "type": "tri-checkbox",
                            "label": "Anti-aliasing quality",
                            "tooltip": "Unchecked = Off, Partially Checked = Fast AA, Checked = Full AA",
                            "key": CARLA_KEY_CANVAS_ANTIALIASING,
                            "default": CARLA_DEFAULT_CANVAS_ANTIALIASING,
                        },
                        {
                            "id": "hq_aa",
                            "type": "checkbox",
                            "label": "4x MSAA multisampling",
                            "tooltip": "High quality multisample anti-aliasing (OpenGL canvas only)",
                            "key": CARLA_KEY_CANVAS_HQ_ANTIALIASING,
                            "default": CARLA_DEFAULT_CANVAS_HQ_ANTIALIASING,
                        },
                    ],
                },
            ],
        },
    ]
}


OSC_SCHEMA = {
    "columns": [
        {
            "id": "col_left",
            "groups": [
                {
                    "title": "Open Sound Control (OSC)",
                    "fields": [
                        {
                            "id": "osc_enabled",
                            "type": "checkbox",
                            "label": "Enable OSC Control Protocol",
                            "key": CARLA_KEY_OSC_ENABLED,
                            "default": CARLA_DEFAULT_OSC_ENABLED,
                        },
                        {
                            "id": "tcp_enabled",
                            "type": "checkbox",
                            "label": "Enable TCP Port",
                            "key": CARLA_KEY_OSC_TCP_PORT_ENABLED,
                            "default": CARLA_DEFAULT_OSC_TCP_PORT_ENABLED,
                            "depends_on": "osc_enabled",
                        },
                        {
                            "id": "tcp_port",
                            "type": "spinbox",
                            "label": "TCP Port number:",
                            "key": CARLA_KEY_OSC_TCP_PORT_NUMBER,
                            "default": CARLA_DEFAULT_OSC_TCP_PORT_NUMBER,
                            "min": 1024,
                            "max": 65535,
                            "depends_on": "tcp_enabled",
                        },
                        {
                            "id": "tcp_random",
                            "type": "checkbox",
                            "label": "Assign random TCP port on launch",
                            "key": CARLA_KEY_OSC_TCP_PORT_RANDOM,
                            "default": CARLA_DEFAULT_OSC_TCP_PORT_RANDOM,
                            "depends_on": "tcp_enabled",
                        },
                    ],
                }
            ],
        },
        {
            "id": "col_right",
            "groups": [
                {
                    "title": "UDP Protocol",
                    "fields": [
                        {
                            "id": "udp_enabled",
                            "type": "checkbox",
                            "label": "Enable UDP Port",
                            "key": CARLA_KEY_OSC_UDP_PORT_ENABLED,
                            "default": CARLA_DEFAULT_OSC_UDP_PORT_ENABLED,
                            "depends_on": "osc_enabled",
                        },
                        {
                            "id": "udp_port",
                            "type": "spinbox",
                            "label": "UDP Port number:",
                            "key": CARLA_KEY_OSC_UDP_PORT_NUMBER,
                            "default": CARLA_DEFAULT_OSC_UDP_PORT_NUMBER,
                            "min": 1024,
                            "max": 65535,
                            "depends_on": "udp_enabled",
                        },
                        {
                            "id": "udp_random",
                            "type": "checkbox",
                            "label": "Assign random UDP port on launch",
                            "key": CARLA_KEY_OSC_UDP_PORT_RANDOM,
                            "default": CARLA_DEFAULT_OSC_UDP_PORT_RANDOM,
                            "depends_on": "udp_enabled",
                        },
                    ],
                }
            ],
        },
    ]
}


WINE_SCHEMA = {
    "columns": [
        {
            "id": "col_left",
            "groups": [
                {
                    "title": "Wine Environment",
                    "fields": [
                        {
                            "id": "wine_exec",
                            "type": "text",
                            "label": "Wine binary executable:",
                            "key": CARLA_KEY_WINE_EXECUTABLE,
                            "default": CARLA_DEFAULT_WINE_EXECUTABLE,
                        },
                        {
                            "id": "auto_prefix",
                            "type": "checkbox",
                            "label": "Automatically detect Wine prefix per binary",
                            "key": CARLA_KEY_WINE_AUTO_PREFIX,
                            "default": CARLA_DEFAULT_WINE_AUTO_PREFIX,
                        },
                        {
                            "id": "fallback_prefix",
                            "type": "path",
                            "label": "Fallback Wine prefix:",
                            "key": CARLA_KEY_WINE_FALLBACK_PREFIX,
                            "default": CARLA_DEFAULT_WINE_FALLBACK_PREFIX,
                        },
                    ],
                }
            ],
        },
        {
            "id": "col_right",
            "groups": [
                {
                    "title": "Realtime Scheduling & Priority",
                    "fields": [
                        {
                            "id": "rt_prio_enabled",
                            "type": "checkbox",
                            "label": "Enable Wine realtime thread scheduling",
                            "key": CARLA_KEY_WINE_RT_PRIO_ENABLED,
                            "default": CARLA_DEFAULT_WINE_RT_PRIO_ENABLED,
                        },
                        {
                            "id": "base_prio",
                            "type": "spinbox",
                            "label": "Base realtime priority:",
                            "key": CARLA_KEY_WINE_BASE_RT_PRIO,
                            "default": CARLA_DEFAULT_WINE_BASE_RT_PRIO,
                            "min": 1,
                            "max": 99,
                            "depends_on": "rt_prio_enabled",
                        },
                        {
                            "id": "server_prio",
                            "type": "spinbox",
                            "label": "Wine server priority:",
                            "key": CARLA_KEY_WINE_SERVER_RT_PRIO,
                            "default": CARLA_DEFAULT_WINE_SERVER_RT_PRIO,
                            "min": 1,
                            "max": 99,
                            "depends_on": "rt_prio_enabled",
                        },
                    ],
                }
            ],
        },
    ]
}


EXPERIMENTAL_SCHEMA = {
    "columns": [
        {
            "id": "col_left",
            "groups": [
                {
                    "title": "Advanced Integration",
                    "fields": [
                        {
                            "id": "jack_apps",
                            "type": "checkbox",
                            "label": "Allow loading standalone JACK applications",
                            "key": CARLA_KEY_EXPERIMENTAL_JACK_APPS,
                            "default": CARLA_DEFAULT_EXPERIMENTAL_JACK_APPS,
                        },
                        {
                            "id": "prevent_bad_behaviour",
                            "type": "checkbox",
                            "label": "Interception hook to prevent plugin crashing loops",
                            "key": CARLA_KEY_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
                            "default": CARLA_DEFAULT_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
                        },
                    ],
                }
            ],
        },
        {
            "id": "col_right",
            "groups": [
                {
                    "title": "Plugin Sandboxing & Bridges",
                    "fields": [
                        {
                            "id": "enable_plugin_bridges",
                            "type": "checkbox",
                            "label": "Enable plugin bridges (experimental)",
                            "key": CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES,
                            "default": CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES,
                            "tooltip": "Master switch for running plugins in a separate bridge process.",
                        },
                        {
                            "id": "prefer_plugin_bridges",
                            "type": "checkbox",
                            "label": "Run plugins in bridge mode when possible",
                            "key": CARLA_KEY_ENGINE_PREFER_PLUGIN_BRIDGES,
                            "default": CARLA_DEFAULT_PREFER_PLUGIN_BRIDGES,
                            "depends_on": "enable_plugin_bridges",
                            "tooltip": "Run plugins in a separate process, so if they crash it does not affect Carla.\nNote: bridged plugins cannot show inline displays on the patchbay canvas.\nNeeds an engine restart to take effect.",
                        },
                        {
                            "id": "plugin_bridges_note",
                            "type": "label",
                            "label": "Inline plugin displays require non-bridged (in-process) LV2 plugins.",
                        },
                    ],
                }
            ],
        },
    ]
}


class SettingsFormBuilder(object):
    """Dynamically builds and binds settings form widgets from a declarative schema."""

    def __init__(self, parent_dialog, schema=None):
        self.dialog = parent_dialog
        self.schema = schema or PATCHBAY_SCHEMA
        self.widgets = {}
        self.field_defs = {}

    def build_page(self, parent_widget):
        """Constructs a responsive 2-column layout inside parent_widget."""
        container = QWidget(parent_widget)
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(12)

        if parent_widget.layout() is not None:
            parent_widget.layout().insertWidget(0, container)
        else:
            outer_layout = QVBoxLayout(parent_widget)
            outer_layout.setContentsMargins(0, 0, 0, 0)
            outer_layout.addWidget(container)

        for col_def in self.schema["columns"]:
            col_container = QWidget(container)
            col_layout = QVBoxLayout(col_container)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(8)

            for group_def in col_def["groups"]:
                group_box = QGroupBox(self.dialog.tr(group_def["title"]), col_container)
                group_layout = QGridLayout(group_box)
                group_layout.setSpacing(6)
                row = 0

                for field in group_def["fields"]:
                    self.field_defs[field["id"]] = field
                    ftype = field["type"]

                    if ftype == "combobox":
                        lbl = QLabel(self.dialog.tr(field["label"]), group_box)
                        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        combo = QComboBox(group_box)
                        self._populate_combo(combo, field)
                        group_layout.addWidget(lbl, row, 0)
                        group_layout.addWidget(combo, row, 1)
                        self.widgets[field["id"]] = combo

                    elif ftype == "slider":
                        lbl = QLabel(self.dialog.tr(field["label"]), group_box)
                        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        slider_box = QHBoxLayout()
                        slider = QSlider(Qt.Horizontal, group_box)
                        slider.setMinimum(field.get("min", 0))
                        slider.setMaximum(field.get("max", 100))
                        suffix = field.get("suffix", "")
                        val_lbl = QLabel(f"{slider.value()}{suffix}", group_box)
                        val_lbl.setMinimumWidth(45)

                        def make_cb(val_w, suf):
                            return lambda v: val_w.setText(f"{v}{suf}")

                        slider.valueChanged.connect(make_cb(val_lbl, suffix))
                        slider_box.addWidget(slider)
                        slider_box.addWidget(val_lbl)

                        group_layout.addWidget(lbl, row, 0)
                        group_layout.addLayout(slider_box, row, 1)
                        self.widgets[field["id"]] = slider
                        self.widgets[f"{field['id']}__val_lbl"] = val_lbl

                    elif ftype in ("checkbox", "tri-checkbox"):
                        chk = QCheckBox(self.dialog.tr(field["label"]), group_box)
                        if ftype == "tri-checkbox":
                            chk.setTristate(True)
                        if "tooltip" in field:
                            chk.setToolTip(self.dialog.tr(field["tooltip"]))
                        group_layout.addWidget(chk, row, 0, 1, 2)
                        self.widgets[field["id"]] = chk

                    elif ftype == "spinbox":
                        lbl = QLabel(self.dialog.tr(field["label"]), group_box)
                        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        sb = QSpinBox(group_box)
                        sb.setMinimum(field.get("min", 0))
                        sb.setMaximum(field.get("max", 65535))
                        group_layout.addWidget(lbl, row, 0)
                        group_layout.addWidget(sb, row, 1)
                        self.widgets[field["id"]] = sb

                    elif ftype == "text":
                        lbl = QLabel(self.dialog.tr(field["label"]), group_box)
                        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        le = QLineEdit(group_box)
                        group_layout.addWidget(lbl, row, 0)
                        group_layout.addWidget(le, row, 1)
                        self.widgets[field["id"]] = le

                    elif ftype == "path":
                        lbl = QLabel(self.dialog.tr(field["label"]), group_box)
                        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        path_box = QHBoxLayout()
                        le = QLineEdit(group_box)
                        btn = QPushButton("...", group_box)
                        btn.setFixedWidth(28)

                        def make_path_cb(line_edit):
                            def _cb():
                                d = QFileDialog.getExistingDirectory(self.dialog, "Choose Directory", line_edit.text())
                                if d:
                                    line_edit.setText(d)
                            return _cb

                        btn.clicked.connect(make_path_cb(le))
                        path_box.addWidget(le)
                        path_box.addWidget(btn)

                        group_layout.addWidget(lbl, row, 0)
                        group_layout.addLayout(path_box, row, 1)
                        self.widgets[field["id"]] = le

                    elif ftype == "label":
                        lbl = QLabel(self.dialog.tr(field["label"]), group_box)
                        lbl.setWordWrap(True)
                        from styles.theme_manager import theme_manager
                        lbl.setStyleSheet("color: %s; font-style: italic;"
                                          % theme_manager.engine.get_token("text-secondary", "#a6adc8"))
                        group_layout.addWidget(lbl, row, 0, 1, 2)

                    row += 1
                col_layout.addWidget(group_box)
            col_layout.addStretch(1)
            main_layout.addWidget(col_container, 1)

        # Wire up inter-field dependencies (e.g. rounded_nodes enables node_radius)
        for fid, fdef in self.field_defs.items():
            dep = fdef.get("depends_on")
            if dep and dep in self.widgets and fid in self.widgets:
                dep_widget = self.widgets[dep]
                target_widget = self.widgets[fid]
                target_val = self.widgets.get(f"{fid}__val_lbl")
                target_widget.setEnabled(dep_widget.isChecked())
                if target_val:
                    target_val.setEnabled(dep_widget.isChecked())

                def make_dep_cb(tw, tv):
                    def _cb(checked):
                        tw.setEnabled(checked)
                        if tv:
                            tv.setEnabled(checked)
                    return _cb

                dep_widget.toggled.connect(make_dep_cb(target_widget, target_val))

    def _populate_combo(self, combo, field):
        factory = field.get("options_factory")
        if factory == "app_themes":
            from styles.theme_manager import theme_manager
            for name in theme_manager.get_available_themes():
                combo.addItem(name)
        elif factory == "line_styles":
            from patchcanvas.linealgos import line_algorithms
            for name, label in line_algorithms():
                combo.addItem(self.dialog.tr(label), name)
        elif "options" in field:
            for item in field["options"]:
                if isinstance(item, tuple):
                    combo.addItem(self.dialog.tr(item[0]), item[1])
                else:
                    combo.addItem(str(item))

    def load_values(self, settings):
        """Loads values from QSafeSettings into form widgets."""
        for fid, fdef in self.field_defs.items():
            widget = self.widgets.get(fid)
            if not widget:
                continue
            key = fdef.get("key")
            if not key:
                continue
            default = fdef.get("default")
            ftype = fdef["type"]

            if ftype == "checkbox":
                val = settings.value(key, bool(default), bool)
                widget.setChecked(bool(val))

            elif ftype == "tri-checkbox":
                val = settings.value(key, int(default), int)
                widget.setCheckState(Qt.CheckState(val))

            elif ftype == "slider" or ftype == "spinbox":
                val = settings.value(key, int(default), int)
                widget.setValue(val)
                val_lbl = self.widgets.get(f"{fid}__val_lbl")
                if val_lbl:
                    val_lbl.setText(f"{val}{fdef.get('suffix', '')}")

            elif ftype in ("combobox", "text", "path"):
                raw_val = settings.value(key, str(default), str)
                if ftype == "combobox":
                    idx = widget.findData(raw_val)
                    if idx < 0:
                        idx = widget.findText(raw_val)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                else:
                    widget.setText(raw_val)

    def save_values(self, settings):
        """Saves current widget values into QSafeSettings and syncs legacy keys."""
        for fid, fdef in self.field_defs.items():
            widget = self.widgets.get(fid)
            if not widget:
                continue
            key = fdef.get("key")
            if not key:
                continue
            ftype = fdef["type"]

            if ftype == "checkbox":
                val = widget.isChecked()
                settings.setValue(key, val)
                for lk in fdef.get("legacy_keys", []):
                    settings.setValue(lk, val)

            elif ftype == "tri-checkbox":
                cs = widget.checkState()
                val = cs.value if hasattr(cs, "value") else int(cs)
                settings.setValue(key, val)

            elif ftype in ("slider", "spinbox"):
                settings.setValue(key, widget.value())

            elif ftype == "combobox":
                data = widget.currentData()
                val = data if data is not None else widget.currentText()
                settings.setValue(key, val)
                if fid == "line_style":
                    settings.setValue(CARLA_KEY_CANVAS_USE_BEZIER_LINES, bool(val == "bezier"))

            elif ftype in ("text", "path"):
                settings.setValue(key, widget.text())

    def reset_defaults(self):
        """Resets all fields to their defined default values."""
        for fid, fdef in self.field_defs.items():
            widget = self.widgets.get(fid)
            if not widget:
                continue
            default = fdef.get("default")
            ftype = fdef["type"]

            if ftype == "checkbox":
                widget.setChecked(bool(default))
            elif ftype == "tri-checkbox":
                widget.setCheckState(Qt.CheckState(default))
            elif ftype in ("slider", "spinbox"):
                widget.setValue(default)
                val_lbl = self.widgets.get(f"{fid}__val_lbl")
                if val_lbl:
                    val_lbl.setText(f"{default}{fdef.get('suffix', '')}")
            elif ftype == "combobox":
                idx = widget.findData(default)
                if idx < 0:
                    idx = widget.findText(default)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif ftype in ("text", "path"):
                widget.setText(str(default))
