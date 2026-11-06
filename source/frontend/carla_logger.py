#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import os
import re
import time
from datetime import datetime
from qt_compat import QObject, pyqtSignal

# Import rich if available, with graceful fallback
try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.text import Text

    _custom_theme = Theme({
        "debug": "dim cyan",
        "info": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "timestamp": "dim white",
        "tag_app": "bold magenta",
        "tag_engine": "bold cyan",
        "tag_patchbay": "bold blue",
        "tag_plugin": "bold green",
        "tag_session": "bold yellow",
        "tag_canvas": "bold bright_magenta",
        "tag_backend": "bold red",
    })
    _rich_console = Console(theme=_custom_theme)
    HAVE_RICH = True
except ImportError:
    _rich_console = None
    HAVE_RICH = False

LOG_LEVEL_DEBUG = 10
LOG_LEVEL_INFO = 20
LOG_LEVEL_WARNING = 30
LOG_LEVEL_ERROR = 40
LOG_LEVEL_CRITICAL = 50

LEVEL_NAMES = {
    LOG_LEVEL_DEBUG: "DEBUG",
    LOG_LEVEL_INFO: "INFO",
    LOG_LEVEL_WARNING: "WARNING",
    LOG_LEVEL_ERROR: "ERROR",
    LOG_LEVEL_CRITICAL: "CRITICAL",
}

NAME_TO_LEVEL = {
    "DEBUG": LOG_LEVEL_DEBUG,
    "INFO": LOG_LEVEL_INFO,
    "WARNING": LOG_LEVEL_WARNING,
    "WARN": LOG_LEVEL_WARNING,
    "ERROR": LOG_LEVEL_ERROR,
    "CRITICAL": LOG_LEVEL_CRITICAL,
}

# Standard tags known throughout the app
KNOWN_TAGS = [
    "APP",
    "ENGINE",
    "PATCHBAY",
    "PLUGIN",
    "SESSION",
    "CANVAS",
    "BACKEND",
]

# ANSI CSI/OSC sequences, plus color codes whose ESC was already stripped by
# an earlier capture layer (which is how "[31m" used to end up as literal text).
_ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_MANGLED_ANSI_RE = re.compile(r"\[[0-9;]{1,8}m")
_ANSI_LEVEL_RE = re.compile(r"\x1b\[([0-9;]*)m")


def _strip_ansi(text):
    if not isinstance(text, str):
        return text
    return _MANGLED_ANSI_RE.sub("", _ANSI_RE.sub("", text))


def _ansi_to_level(text):
    """Map a red/yellow ANSI prefix to a level before the codes are stripped."""
    if not isinstance(text, str):
        return None
    codes = _ANSI_LEVEL_RE.findall(text) + _MANGLED_ANSI_RE.findall(text)
    for code in codes:
        parts = code.strip("[]m").split(";")
        if "31" in parts or "91" in parts:
            return LOG_LEVEL_ERROR
        if "33" in parts or "93" in parts:
            return LOG_LEVEL_WARNING
    return None


class LogEntry:
    __slots__ = ("timestamp", "level", "tag", "message", "raw_text")

    def __init__(self, level, tag, message, raw_text=""):
        self.timestamp = datetime.now()
        self.level = level
        self.tag = tag.upper().strip("[] ") if tag else "APP"
        self.message = _strip_ansi(message)
        self.raw_text = raw_text or f"[{self.tag}] {message}"

    def formatted_ui(self):
        time_str = self.timestamp.strftime("%H:%M:%S")
        lvl_str = LEVEL_NAMES.get(self.level, "INFO")
        return f"{time_str}  {lvl_str:<8} {self.tag:<10} {self.message}"

class CarlaLogger(QObject):
    logAdded = pyqtSignal(object)  # Emits LogEntry

    def __init__(self):
        super().__init__()
        # Only mirror logs to the terminal when one is actually attached. GUI
        # launches (no tty) previously paid for rich rendering every line for
        # output nobody could see, which froze the UI under backend log floods.
        self.console_enabled = sys.stdout.isatty()
        self.min_level = LOG_LEVEL_INFO
        self.whitelist = set()  # if non-empty, only these tags shown
        self.blacklist = set()  # these tags hidden
        self.history = []       # all LogEntry objects stored
        self.max_history = 5000
        self._last_msg = None
        self._repeat_count = 0
        self._assertion_seen = {}
        # Terminal output is capped so a backend log flood cannot peg the CPU
        # rendering rich text nobody can read fast enough.
        self._console_max_per_sec = 60
        self._console_window_start = 0.0
        self._console_window_count = 0
        self._console_suppressed = 0

    def parse_cli_args(self, args=None):
        if args is None:
            args = sys.argv[1:]

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--log-level" and i + 1 < len(args):
                lvl_str = args[i + 1].upper()
                if lvl_str in NAME_TO_LEVEL:
                    self.min_level = NAME_TO_LEVEL[lvl_str]
                i += 1
            elif arg == "--log-whitelist" and i + 1 < len(args):
                tags = [t.strip().upper() for t in args[i + 1].split(",") if t.strip()]
                self.whitelist.update(tags)
                i += 1
            elif arg == "--log-blacklist" and i + 1 < len(args):
                tags = [t.strip().upper() for t in args[i + 1].split(",") if t.strip()]
                self.blacklist.update(tags)
                i += 1
            elif arg == "--no-console-log":
                self.console_enabled = False
            elif arg == "--console-log":
                self.console_enabled = True
            i += 1

    def is_tag_active(self, tag):
        tag = tag.upper()
        if self.whitelist and tag not in self.whitelist:
            return False
        if tag in self.blacklist:
            return False
        return True

    def should_display(self, entry):
        if entry.level < self.min_level:
            return False
        return self.is_tag_active(entry.tag)

    def _console_budget_ok(self):
        """Consume one terminal-print token; False when over the rate limit."""
        now = time.monotonic()
        if now - self._console_window_start >= 1.0:
            self._console_window_start = now
            self._console_window_count = 0
            if self._console_suppressed:
                suppressed = self._console_suppressed
                self._console_suppressed = 0
                self._console_window_count += 1
                self._print_terminal(LogEntry(
                    LOG_LEVEL_WARNING, "APP",
                    f"[console throttled: {suppressed} lines suppressed]"))
        if self._console_window_count < self._console_max_per_sec:
            self._console_window_count += 1
            return True
        self._console_suppressed += 1
        return False

    def log(self, level, tag, message):
        if isinstance(message, str) and "assertion failure" in message.lower():
            # Repeating assertions (autosave, engine teardown) add no new information.
            now = time.monotonic()
            key = (tag, message)
            last, count = self._assertion_seen.get(key, (0.0, 0))
            if now - last < 300.0:
                self._assertion_seen[key] = (last, count + 1)
                return
            if count:
                message = f"{message} (+{count} repeats suppressed)"
            self._assertion_seen[key] = (now, 0)
        msg_key = (tag, message)
        if msg_key == self._last_msg:
            self._repeat_count += 1
            if self._repeat_count > 2:
                # Suppress spamming identical consecutive messages
                return
        else:
            if self._repeat_count > 2 and self.console_enabled:
                repeat_entry = LogEntry(LOG_LEVEL_DEBUG, "APP", f"[previous message repeated {self._repeat_count} times]")
                if self.should_display(repeat_entry):
                    self._print_terminal(repeat_entry)
            self._last_msg = msg_key
            self._repeat_count = 1

        entry = LogEntry(level, tag, message)
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Output to terminal if enabled (rate-limited so floods cannot peg CPU)
        if self.console_enabled and self.should_display(entry):
            if self._console_budget_ok():
                self._print_terminal(entry)

        # Emit to UI
        self.logAdded.emit(entry)

    def _print_terminal(self, entry):
        lvl_name = LEVEL_NAMES.get(entry.level, "INFO")
        time_str = entry.timestamp.strftime("%H:%M:%S")

        if HAVE_RICH and _rich_console is not None:
            style_name = lvl_name.lower()
            tag_style = f"tag_{entry.tag.lower()}"
            if tag_style not in _custom_theme.styles:
                tag_style = "tag_app"
            text = Text()
            text.append(f"{time_str}  ", style="timestamp")
            text.append(f"{lvl_name:<8} ", style=style_name)
            text.append(f"{entry.tag:<10} ", style=tag_style)
            text.append(entry.message, style="dim" if entry.level == LOG_LEVEL_DEBUG else "")
            _rich_console.print(text, soft_wrap=True)
        else:
            out = getattr(self, "_terminal_out", None) or sys.stdout
            print(f"{time_str}  {lvl_name:<8} {entry.tag:<10} {entry.message}", file=out)

    def debug(self, tag, message):
        self.log(LOG_LEVEL_DEBUG, tag, message)

    def info(self, tag, message):
        self.log(LOG_LEVEL_INFO, tag, message)

    def warning(self, tag, message):
        self.log(LOG_LEVEL_WARNING, tag, message)

    def error(self, tag, message):
        self.log(LOG_LEVEL_ERROR, tag, message)

    def critical(self, tag, message):
        self.log(LOG_LEVEL_CRITICAL, tag, message)

    def log_raw_string(self, text, explicit_level=None):
        """Parse raw incoming string from legacy logs and classify tag/level"""
        if not text:
            return

        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")

        # Read colours before stripping: C++ logs often report severity only
        # through the ANSI prefix (red = error, yellow = warning).
        ansi_level = _ansi_to_level(text)

        # ANSI first: dropping the ESC byte first would leave "[31m" in the text.
        text = _strip_ansi(text)

        # Strip non-printable and binary control characters (except tab/newline)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

        level = explicit_level if explicit_level is not None else LOG_LEVEL_INFO
        tag = "APP"
        clean_text = text.strip()
        if not clean_text:
            return

        # Filter noisy benign messages
        upper_text = clean_text.upper()
        benign_noise = (
            "CANREAD",
            "GROUPNAME != NULLPTR",
            "TEMPORARYFILE",
            "ID < PDATA->CURPLUGINCOUNT",
            "SIZE < FBUFFER->SIZE",
            "EXISTSASFILE",
            "PLUGIN.GET() != NULLPTR",
            "UNABLE TO FIND GROUP TO REMOVE",
            "LILV_WORLD_ADD_PLUGIN(): WARNING: DUPLICATE PLUGIN",
            "CARLA_V3_COMPONENT_HANDLER::QUERY_INTERFACE",
            "CARLAPLUGINBRIDGETHREAD::RUN() - BRIDGE AUTO-CLOSED",
            "REMAINING BUFFERS ON DESTRUCTION",
            "TOTAL SIZE: 0",
            "KF.ICONTHEMES",
            "ICON THEME",
            "FRONTEND PIXEL RATIO IS",
            "DEVICEPIXELRATIO",
            "ENGINE_CALLBACK_PATCHBAY",
            "PATCHBAY_CLIENT_ADDED",
            "PATCHBAY_CLIENT_REMOVED",
            "PATCHBAY_CLIENT_RENAMED",
            "PATCHBAY_PORT_ADDED",
            "PATCHBAY_PORT_REMOVED",
            "PATCHBAY_CONNECTION_ADDED",
            "PATCHBAY_CONNECTION_REMOVED",
            "SLOT_HANDLEPATCHBAY",
            "SLOT_HANDLEPLUGINADDEDCALLBACK",
            "PYPLUGINLISTDIALOG: SET_OPTION FAILED",
            "PYPLUGINLISTDIALOG: FAILED TO CHECK GLOBAL SCANNER",
            "WHICH IS NOT AVAILABLE",
            "REQUESTED UNSUPPORTED CLAP EXTENSION",
            "THE ENUMERATION HAS AN INVALID RANGE",
            "[WINE STDERR]",
            "PCI ID FOR FD",
            "YABRIDGE-HOST.EXE",
            "LIBYABRIDGE",
            "STARTING PLUGIN BRIDGE",
            "CARLA BRIDGE READY",
            "WITH REALTIME PRIORITY SUCCESSFUL",
            "CARLA_SHM_CREATE_TEMP",
            "WAITFORSAVED",
            "QT.QPA.WAYLAND",
            "WAYLANDTEXTINPUT",
            "DISABLESURFACE",
            "QT.SVG: INVALID PATH DATA",
            "QFONT::SETPIXELSIZE",
            "RENDER GLYPH FAILED",
            "MAPPING ABSOLUTEPATH",
            "GETSTATEINFORMATION CALLED",
            "STATE SAVED. TOTAL SIZE",
            "[CLAP SCANNER] FOUND",
            "[SCANNER] FOUND",
            "[CLAP SCANNER] SCANNING",
            "CLAP SCAN COMPLETE",
            "CLAP PLUGINS ADDED",
            "SIZE > 0",
            "! PDATA->LOADINGPROJECT",
            "VAR.SIZE >= SIZE",
            "INITIALIZING YABRIDGE",
            "HOSTING MODE:",
            "ENABLED FEATURES:",
            "BITBRIDGE SUPPORT",
            "WINE PREFIX:",
            "WINE VERSION:",
            "OTHER OPTIONS:",
            "SOCKETS:",
            "CONFIG FROM:",
            "URID < FCUSTOMURIDS.SIZE()",
            "UNSUPPORTED KVT ITEM TYPE",
            "PLUGIN UI WANTS A FEATURE THAT IS NOT SUPPORTED",
            "HTTP://LV2PLUG.IN/NS/EXT/OPTIONS#INTERFACE",
            "GOT UNKNOWN PORT DESIGNATION",
            "=== CONSTRUCTOR START ===",
            "=== CONSTRUCTOR DONE ===",
            "SCANNING VST3...",
            "VST3 PLUGINS FOUND",
            "DEFERRING CLAP SCAN",
            "VST3 PLUGINS AVAILABLE IMMEDIATELY",
            "SETSTATEINFORMATION CALLED",
            "STATE RESTORED",
            "STARTING DEFERRED CLAP SCAN",
            "SKIPPING SELF:",
            "CLAP_PLUGIN_GUI.CAN_RESIZE()",
            "IT IS WRONG TO QUERY THE LATENCY",
            "[CLAP HOST]",
            "MODEL AND ENGINE GRAPH COUNTS DO NOT MATCH",
            "LOG PATH:",
            "CHECKING DESKTOPFILE AT:",
            "MAPPING ABSOLUTEPATH",
            "MAPPING ABSTRACTPATH",
            "CREATING SYMLINK FOR",
            "NUMBER OF MASTERS:",
            "NUMBER OF GROUPS:",
            "NUMBER OF REGIONS:",
            "FILE CHANGED TO:",
            "AUDIOMASTERAUTOMATE CALLED FROM UNKNOWN SOURCE",
            "WILL USE LV2 X11 UI FOR",
            "PREVIOUSLY SAVED CLIENT",
        )
        is_yabridge_line = bool(re.search(r'\[[\w\.-]+-[A-Za-z0-9]{8}\]', clean_text))
        if "ASSERTION FAILURE" in upper_text:
            # Always an error, even when the asserted expression looks benign.
            level = LOG_LEVEL_ERROR
            tag = "BACKEND"
        elif is_yabridge_line or any(b in upper_text for b in benign_noise):
            level = LOG_LEVEL_DEBUG
            if tag in ("APP", "WRN"):
                if "PATCHBAY" in upper_text:
                    tag = "PATCHBAY"
                elif "PLUGIN" in upper_text or "SCANNER" in upper_text or "CLAP" in upper_text or "KVT" in upper_text:
                    tag = "PLUGIN"
                elif "ENGINE" in upper_text:
                    tag = "ENGINE"
                elif is_yabridge_line or "WINE" in upper_text or "YABRIDGE" in upper_text or "BRIDGE" in upper_text:
                    tag = "BRIDGE"
                else:
                    tag = "BACKEND"
        elif explicit_level is None:
            if "ERROR" in upper_text or "CRITICAL" in upper_text or "FAIL" in upper_text:
                level = LOG_LEVEL_ERROR
            elif "WARN" in upper_text:
                level = LOG_LEVEL_WARNING
            elif "DEBUG" in upper_text:
                level = LOG_LEVEL_DEBUG
            elif ansi_level is not None:
                level = ansi_level

        # Look for [carla] prefix (e.g. from backend assertions / logging);
        # interleaved stdout can also put it in the middle of a line.
        if clean_text.startswith("[carla]"):
            tag = "BACKEND"
            clean_text = clean_text[7:].strip()
        if "[carla]" in clean_text:
            clean_text = clean_text.replace("[carla] ", "").replace("[carla]", "").strip()
        else:
            # Look for general [TAG] pattern at the start
            m = re.match(r"^\[([A-Za-z0-9_\-]+)\]\s*(.*)$", clean_text)
            if m:
                tag_candidate = m.group(1).upper()
                if tag_candidate in KNOWN_TAGS or tag_candidate not in ("CARLA",):
                    tag = tag_candidate
                clean_text = m.group(2)
            elif "PATCH" in upper_text or "CANVAS" in upper_text:
                tag = "PATCHBAY"
            elif "PLUGIN" in upper_text or "SFIZZ" in upper_text or "VST" in upper_text or "CLAP" in upper_text or "LV2" in upper_text:
                tag = "PLUGIN"
            elif "ENGINE" in upper_text:
                tag = "ENGINE"
        self.log(level, tag, clean_text)

    def _capture_fd(self, fd):
        import threading
        pipe_r, pipe_w = os.pipe()
        os.dup2(pipe_w, fd)
        os.close(pipe_w)

        def _reader():
            # Read binary chunks and split by newline to handle non-UTF8/binary pollution
            buf = bytearray()
            while True:
                try:
                    chunk = os.read(pipe_r, 4096)
                    if not chunk:
                        break
                    buf.extend(chunk)
                    while b"\n" in buf:
                        line, _, buf = buf.partition(b"\n")
                        decoded_line = line.strip(b"\r\n ").decode("utf-8", errors="replace")
                        if decoded_line:
                            self.log_raw_string(decoded_line)
                except Exception:
                    break

        threading.Thread(target=_reader, daemon=True).start()

    def start_capturing_stderr(self):
        """Intercept C/C++ backend stderr (fd 2) and route output through CarlaLogger"""
        if getattr(self, "_stderr_captured", False):
            return
        self._stderr_captured = True
        try:
            self._orig_stderr_fd = os.dup(2)
            self._capture_fd(2)
        except Exception as e:
            print("CarlaLogger: failed to capture backend stderr:", e)

    def start_capturing_stdout(self):
        """Intercept C/C++ backend and bridge stdout (fd 1) too, so [carla] lines
        are formatted and filtered instead of leaking raw to the terminal."""
        if getattr(self, "_stdout_captured", False):
            return
        self._stdout_captured = True
        try:
            global _rich_console
            self._orig_stdout_fd = os.dup(1)
            self._terminal_out = os.fdopen(
                os.dup(1), "w", buffering=1, encoding="utf-8", errors="replace")
            if HAVE_RICH:
                _rich_console = Console(theme=_custom_theme, file=self._terminal_out)
            self._capture_fd(1)
        except Exception as e:
            print("CarlaLogger: failed to capture backend stdout:", e)

# Singleton global instance
logger = CarlaLogger()

