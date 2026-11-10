"""Centralized Theme Registry for Clara.

Maintains lean Base16 / Base24 palette definitions and provides registry lookups
with automatic mode resolution and direct Base16/Base24 ingestion.
"""

import copy
import json
import os
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------------------------------------------------
# Bundled Base16/Base24 Lean Theme Palettes
# ------------------------------------------------------------------------------------------------------------

BUILTIN_THEMES: Dict[str, Dict[str, Any]] = {
    "Catppuccin Macchiato": {
        "name": "Catppuccin Macchiato",
        "author": "Catppuccin Org",
        "mode": "dark",
        "palette": {
            "base00": "#181926",  # Crust / Base
            "base01": "#1e2030",  # Mantle / Surface0
            "base02": "#24273a",  # Surface1
            "base03": "#363a4f",  # Surface2 / Border
            "base04": "#5b6078",  # Overlay0 / Muted
            "base05": "#cad3f5",  # Text
            "base06": "#f4dbd6",  # Rosewater
            "base07": "#b7bdf8",  # Lavender
            "base08": "#ed8796",  # Red
            "base09": "#f5a97f",  # Peach / Orange
            "base0A": "#eed49f",  # Yellow
            "base0B": "#a6da95",  # Green
            "base0C": "#8bd5ca",  # Teal / Cyan
            "base0D": "#8aadf4",  # Blue (Accent)
            "base0E": "#c6a0f6",  # Mauve / Purple
            "base0F": "#f0c6c6",  # Flamingo / Pink
        },
    },

    "Catppuccin Mocha": {
        "name": "Catppuccin Mocha",
        "author": "Catppuccin Org",
        "mode": "dark",
        "palette": {
            "base00": "#11111b",  # Crust
            "base01": "#181825",  # Mantle
            "base02": "#1e1e2e",  # Base
            "base03": "#313244",  # Surface0
            "base04": "#6c7086",  # Overlay0
            "base05": "#cdd6f4",  # Text
            "base06": "#f5e0dc",  # Rosewater
            "base07": "#b4befe",  # Lavender
            "base08": "#f38ba8",  # Red
            "base09": "#fab387",  # Peach
            "base0A": "#f9e2af",  # Yellow
            "base0B": "#a6e3a1",  # Green
            "base0C": "#94e2d5",  # Teal
            "base0D": "#89b4fa",  # Blue
            "base0E": "#cba6f7",  # Mauve
            "base0F": "#f2cdcd",  # Flamingo
        },
    },

    "Clara Light": {
        "name": "Clara Light",
        "author": "Clara Audio",
        "mode": "light",
        "palette": {
            "base00": "#f7f7fa",  # Window
            "base01": "#eceef4",  # Surface
            "base02": "#e1e4ed",  # Hover / selected
            "base03": "#c6cad8",  # Border
            "base04": "#6e7484",  # Muted text
            "base05": "#23252d",  # Text
            "base06": "#43464f",
            "base07": "#14161c",
            "base08": "#c0392b",  # Red
            "base09": "#b35c00",  # Orange
            "base0A": "#8a6a00",  # Yellow
            "base0B": "#2e7d32",  # Green
            "base0C": "#00727c",  # Teal
            "base0D": "#1f5fbf",  # Blue (Accent)
            "base0E": "#7b3ec8",  # Purple
            "base0F": "#b02a5c",  # Pink
        },
    },

    "Classic Dark": {
        "name": "Classic Dark",
        "author": "Clara Audio",
        "mode": "dark",
        "palette": {
            "base00": "#1e1e1e",
            "base01": "#222222",
            "base02": "#282828",
            "base03": "#3c3c3c",
            "base04": "#666666",
            "base05": "#e0e0e0",
            "base06": "#eeeeee",
            "base07": "#ffffff",
            "base08": "#e06c75",  # Red
            "base09": "#d19a66",  # Orange
            "base0A": "#e5c07b",  # Yellow
            "base0B": "#98c379",  # Green
            "base0C": "#56b6c2",  # Cyan
            "base0D": "#4a90e2",  # Audio Blue Accent
            "base0E": "#c678dd",  # Purple
            "base0F": "#be5046",  # Magenta
        },
    },

    "Nord": {
        "name": "Nord",
        "author": "Arctic Ice Studio",
        "mode": "dark",
        "palette": {
            "base00": "#242933",  # Polar Night darkest
            "base01": "#2e3440",  # Polar Night dark
            "base02": "#3b4252",  # Polar Night medium
            "base03": "#4c566a",  # Polar Night bright / border
            "base04": "#d8dee9",  # Snow Storm dark
            "base05": "#e5e9f0",  # Snow Storm medium
            "base06": "#eceff4",  # Snow Storm bright
            "base07": "#8fbcbb",  # Frost
            "base08": "#bf616a",  # Red
            "base09": "#d08770",  # Orange
            "base0A": "#ebcb8b",  # Yellow
            "base0B": "#a3be8c",  # Green
            "base0C": "#88c0d0",  # Frost Cyan
            "base0D": "#81a1c1",  # Frost Blue Accent
            "base0E": "#b48ead",  # Aurora Purple
            "base0F": "#5e81ac",  # Frost Dark Blue
        },
    },

    "Tokyo Night": {
        "name": "Tokyo Night",
        "author": "Enki",
        "mode": "dark",
        "palette": {
            "base00": "#16161e",
            "base01": "#1a1b26",
            "base02": "#24283b",
            "base03": "#414868",
            "base04": "#565f89",
            "base05": "#a9b1d6",
            "base06": "#c0caf5",
            "base07": "#cfc9c2",
            "base08": "#f7768e",
            "base09": "#ff9e64",
            "base0A": "#e0af68",
            "base0B": "#9ece6a",
            "base0C": "#7dcfff",
            "base0D": "#7aa2f7",
            "base0E": "#bb9af7",
            "base0F": "#f7768e",
        },
    },

    "Dracula": {
        "name": "Dracula",
        "author": "Zeno Rocha",
        "mode": "dark",
        "palette": {
            "base00": "#1e1f29",
            "base01": "#282a36",
            "base02": "#44475a",
            "base03": "#6272a4",
            "base04": "#f8f8f2",
            "base05": "#f8f8f2",
            "base06": "#bd93f9",
            "base07": "#ff79c6",
            "base08": "#ff5555",
            "base09": "#ffb86c",
            "base0A": "#f1fa8c",
            "base0B": "#50fa7b",
            "base0C": "#8be9fd",
            "base0D": "#bd93f9",
            "base0E": "#ff79c6",
            "base0F": "#ff5555",
        },
    },

    "Gruvbox Dark": {
        "name": "Gruvbox Dark",
        "author": "morhetz",
        "mode": "dark",
        "palette": {
            "base00": "#1d2021",
            "base01": "#282828",
            "base02": "#3c3836",
            "base03": "#504945",
            "base04": "#bdae93",
            "base05": "#d5c4a1",
            "base06": "#ebdbb2",
            "base07": "#fbf1c7",
            "base08": "#fb4934",
            "base09": "#fe8019",
            "base0A": "#fabd2f",
            "base0B": "#b8bb26",
            "base0C": "#8ec07c",
            "base0D": "#83a598",
            "base0E": "#d3869b",
            "base0F": "#d65d0e",
        },
    },
}

class ThemeRegistry:
    """Central registry for storing, looking up, and registering Base16/Base24 themes."""

    _instance: Optional["ThemeRegistry"] = None

    def __init__(self):
        self._themes: Dict[str, Dict[str, Any]] = copy.deepcopy(BUILTIN_THEMES)

    @classmethod
    def instance(cls) -> "ThemeRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_theme_names(self) -> List[str]:
        return list(self._themes.keys())

    def get_theme(self, name: str, mode: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Lookup a theme by name.

        If `mode` ('light' or 'dark') is specified and differs from the theme's native mode,
        the ThemeEngine will automatically invert the grayscale luminance range.
        """
        key = name.strip()
        # Direct match
        theme = self._themes.get(key)
        if not theme:
            # Case-insensitive match
            for k, v in self._themes.items():
                if k.lower() == key.lower():
                    theme = v
                    break
        if not theme:
            return None

        result = copy.deepcopy(theme)
        if mode:
            result["requested_mode"] = mode.lower()
        return result

    def register_theme(
        self,
        name: str,
        palette: Dict[str, str],
        mode: str = "dark",
        author: str = "User",
        overrides: Optional[Dict[str, str]] = None,
    ):
        """Register a new Base16 / Base24 theme definition directly into the registry."""
        self._themes[name] = {
            "name": name,
            "author": author,
            "mode": mode.lower(),
            "palette": palette,
            "overrides": overrides or {},
        }

    def ingest_base16_file(self, file_path: str, name: Optional[str] = None) -> str:
        """Ingest a standard Base16 / Base24 YAML or JSON file directly."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        data: Dict[str, Any] = {}
        if file_path.endswith(".json"):
            data = json.loads(content)
        else:
            # Simple line-by-line YAML parser for Base16 schemes (avoids pyyaml dependency)
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().strip("'\"")
                    v = v.strip().strip("'\"")
                    data[k] = v

        theme_name = name or data.get("scheme", data.get("name", os.path.splitext(os.path.basename(file_path))[0]))
        palette: Dict[str, str] = {}
        for i in range(16):
            key = f"base0{i:X}"
            if key in data:
                palette[key] = data[key]
        for i in range(16, 24):
            key = f"base{i:X}"
            if key in data:
                palette[key] = data[key]

        author = data.get("author", "Unknown")
        self.register_theme(theme_name, palette, mode="dark", author=author)
        return theme_name

registry = ThemeRegistry.instance()

def get_theme(name: str, mode: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return registry.get_theme(name, mode)

def list_themes() -> List[str]:
    return registry.list_theme_names()
