#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Clara single-instance lock + local control channel (Qt).
# The lock is the source of truth; the socket is only the transport.

import argparse
import json
import os
import re
import sys
import time

from qt_compat import (
    QCoreApplication,
    QLockFile,
    QLocalServer,
    QLocalSocket,
    QObject,
    QTimer,
    pyqtSignal,
)

from clara_instance_core import (
    MAX_REQUEST_BYTES,
    PROTOCOL_VERSION,
    ProtocolError,
    build_reply,
    build_request,
    decode_request,
    encode_reply,
    encode_request,
    error_reply,
)

MAX_CONNECTIONS = 16
REPLY_CLOSE_DELAY_MS = 250


def _ensure_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


class InstanceLock(object):
    """Atomic GUI-instance lock. The OS releases it when the process dies."""

    def __init__(self, path):
        self.path = path
        self.lock = QLockFile(path)
        # Rely on PID/hostname stale detection, never on elapsed time.
        self.lock.setStaleLockTime(0)

    def acquire(self, timeout_ms=0):
        return bool(self.lock.tryLock(timeout_ms))

    def release(self):
        try:
            self.lock.unlock()
        except Exception:
            pass

    def owner_pid(self):
        try:
            ok, pid, _hostname, _appname = self.lock.getLockInfo()
            return pid if ok else None
        except Exception:
            return None


class MsgServer(QObject):
    showRequested = pyqtSignal()

    def __init__(self, socket_path, handler, parent=None):
        super(MsgServer, self).__init__(parent)
        self.socket_path = socket_path
        self.handler = handler
        self.server = QLocalServer(self)
        option = getattr(QLocalServer, "UserAccessOption", None)
        if option is None:
            option = QLocalServer.SocketOption.UserAccessOption
        self.server.setSocketOptions(option)
        self.server.newConnection.connect(self._on_new_connection)
        self._sockets = set()

    def start(self, remove_stale=False):
        if remove_stale:
            QLocalServer.removeServer(self.socket_path)
        if not self.server.listen(self.socket_path):
            return False
        if os.name != "nt":
            try:
                os.chmod(self.socket_path, 0o600)
            except OSError:
                pass
        return True

    def close(self):
        for sock in list(self._sockets):
            try:
                sock.abort()
            except RuntimeError:
                pass
        self._sockets.clear()
        if self.server.isListening():
            self.server.close()
            if os.name != "nt":
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass

    def _on_new_connection(self):
        sock = self.server.nextPendingConnection()
        if sock is None:
            return
        if len(self._sockets) >= MAX_CONNECTIONS:
            sock.abort()
            return
        self._sockets.add(sock)
        sock.setProperty("clara_buffer", b"")
        sock.readyRead.connect(lambda s=sock: self._on_ready_read(s))
        sock.disconnected.connect(lambda s=sock: self._on_disconnected(s))
        if sock.bytesAvailable():
            self._on_ready_read(sock)

    def _on_disconnected(self, sock):
        self._sockets.discard(sock)
        sock.deleteLater()

    def _on_ready_read(self, sock):
        try:
            buf = bytes(sock.property("clara_buffer") or b"") + bytes(sock.readAll())
        except RuntimeError:
            return
        sock.setProperty("clara_buffer", buf)
        if len(buf) > MAX_REQUEST_BYTES:
            self._send(sock, error_reply("bad_request", "request too large"))
            return
        stripped = buf.lstrip()
        if not stripped:
            return
        if stripped.startswith(b"{"):
            if b"\n" not in buf:
                return  # wait for the terminating newline
            line, _rest = buf.split(b"\n", 1)
        else:
            # Legacy fire-and-forget clients send SHOW without a newline.
            line = buf
        self._dispatch(sock, line)

    def _dispatch(self, sock, raw):
        try:
            request = decode_request(raw)
        except ProtocolError as exc:
            self._send(sock, error_reply(exc.code, exc.message))
            return

        if request.get("cmd") == "show":
            # Reply first, raise the window on the next event-loop turn.
            if request.get("legacy"):
                self._send_raw(sock, b"OK")
            else:
                self._send(sock, build_reply(True))
            QTimer.singleShot(0, self.showRequested.emit)
            return

        try:
            if self.handler is None:
                reply = error_reply("unsupported", "no command handler")
            else:
                reply = self.handler(request)
                if reply is None:
                    reply = error_reply("internal", "empty reply")
        except Exception as exc:
            reply = error_reply("internal", str(exc))
        self._send(sock, reply)

    def _send(self, sock, reply):
        data = encode_reply(reply)
        if len(data) > 8 * 1024 * 1024:
            data = encode_reply(error_reply("internal", "reply too large"))
        self._send_raw(sock, data)

    def _close_socket(self, sock):
        try:
            sock.disconnectFromServer()
        except RuntimeError:
            pass

    def _send_raw(self, sock, data):
        try:
            sock.write(data)
            sock.flush()
        except (RuntimeError, OSError):
            return
        # flush() hands the bytes to the OS; close a moment later without blocking the UI.
        QTimer.singleShot(REPLY_CLOSE_DELAY_MS, lambda s=sock: self._close_socket(s))


class MsgClient(object):
    @staticmethod
    def request(socket_path, payload, timeout_ms=3000):
        """Send raw bytes, return the raw reply bytes, or None."""
        _ensure_app()
        sock = QLocalSocket()
        sock.connectToServer(socket_path)
        if not sock.waitForConnected(timeout_ms):
            return None
        try:
            sock.write(payload)
            sock.flush()
            deadline_reads = 20
            data = b""
            while deadline_reads > 0:
                app = QCoreApplication.instance()
                if app is not None:
                    app.processEvents()
                if sock.bytesAvailable():
                    data += bytes(sock.readAll())
                    if data.endswith(b"\n") or data == b"OK":
                        break
                if not sock.waitForReadyRead(150):
                    deadline_reads -= 1
                    continue
                deadline_reads = 20
            return data or None
        finally:
            try:
                sock.disconnectFromServer()
            except Exception:
                pass


def forward_to_primary(socket_path, project=None, timeout_ms=8000):
    """Returns (ok, message). Sends OPEN when a project is given, else SHOW.
    Retries while the primary is still starting and has not bound its socket yet."""
    if project and os.path.isfile(project):
        payload = encode_request(build_request("open", path=os.path.abspath(project)))
    else:
        payload = b"SHOW"
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    raw = None
    debug = os.environ.get("CLARA_DEBUG_INSTANCE")
    started = time.monotonic()
    while raw is None:
        raw = MsgClient.request(socket_path, payload, 500)
        if debug:
            try:
                with open("/tmp/clara-instance-debug.log", "a") as f:
                    f.write("%.3f pid=%s socket=%s attempt=%.3f reply=%r\n" % (
                        started, os.getpid(), os.path.exists(socket_path), time.monotonic() - started, raw))
            except OSError:
                pass
        if raw is not None:
            break
        if time.monotonic() >= deadline:
            return False, "no reply"
        app = QCoreApplication.instance()
        if app is not None:
            app.processEvents()
        time.sleep(0.1)
    text = raw.strip()
    if text == b"OK":
        return True, "ok"
    try:
        reply = json.loads(text.decode("utf-8", "replace"))
    except ValueError:
        return False, "invalid reply"
    if reply.get("ok"):
        return True, "ok"
    return False, (reply.get("error") or {}).get("message", "request failed")


def socket_is_live(socket_path, timeout_ms=600):
    """True when something answers on the socket (old or new instance)."""
    return MsgClient.request(socket_path, b"SHOW", timeout_ms) is not None


# ----------------------------------------------------------------------------------------------------------------------
# CLI

def _node_line(node):
    container = node.get("container") or "-"
    return "%-6s %-8s %-32s %4sx%-4s %s" % (
        node.get("id"), node.get("kind", ""), node.get("name", ""),
        node.get("w", 0), node.get("h", 0), container,
    )


def _print_nodes_table(data, tree):
    nodes = data.get("nodes", [])
    if not tree:
        print("%-6s %-8s %-32s %-9s %s" % ("ID", "KIND", "NAME", "SIZE", "CONTAINER"))
        for node in nodes:
            print(_node_line(node))
        return

    by_container = {}
    loose = []
    for node in nodes:
        if node.get("container_id") is not None:
            by_container.setdefault(node["container_id"], []).append(node)
        else:
            loose.append(node)
    for container in data.get("containers", []):
        print("%s (%s)" % (container.get("title"), container.get("layout")))
        for node in by_container.get(container.get("id"), []):
            print("  " + _node_line(node))
    if loose:
        print("loose")
        for node in loose:
            print("  " + _node_line(node))


def _print_connections_table(data):
    for conn in data.get("connections", []):
        print("%s:%s -> %s:%s" % (
            conn["src"].get("node_name"), conn["src"].get("port"),
            conn["dst"].get("node_name"), conn["dst"].get("port"),
        ))


def _print_containers_table(data):
    print("%-6s %-24s %-9s %s" % ("ID", "TITLE", "LAYOUT", "MEMBERS"))
    for container in data.get("containers", []):
        print("%-6s %-24s %-9s %s" % (
            container.get("id"), container.get("title"),
            container.get("layout"), ", ".join(container.get("members", [])),
        ))


def _emit_error(message):
    """Client errors bypass the logger's stderr capture."""
    try:
        from carla_logger import logger
        fd = getattr(logger, "_orig_stderr_fd", None)
        if fd is not None:
            os.write(fd, (str(message) + "\n").encode("utf-8", "replace"))
            return
    except Exception:
        pass
    print(message, file=sys.__stderr__)


def _send(socket_path, request):
    raw = MsgClient.request(socket_path, encode_request(request))
    if raw is None:
        _emit_error("Clara is not running.")
        return None
    try:
        reply = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        _emit_error("invalid reply from Clara")
        return None
    if not reply.get("ok"):
        _emit_error((reply.get("error") or {}).get("message", "request failed"))
        return None
    # The running instance loaded its code at startup; edits on disk never
    # reach it. Warn loudly instead of letting fixes "not work" mysteriously.
    try:
        from clara_instance_core import code_stamp
        theirs = ((reply.get("data") or {}).get("code_version"))
        mine = code_stamp()
        if theirs and mine and theirs != mine and not os.environ.get("CLARA_SKIP_STALE_CHECK"):
            print("warning: the running Clara instance predates the code on "
                  "disk (instance %s, disk %s); restart it to test recent "
                  "changes." % (theirs, mine))
    except Exception:
        pass
    return reply


_HELP_TEMPLATE = """{prog} - control a running Clara instance

Run `{prog} --examples` for a full list of copy-paste examples.

USAGE
  {prog} COMMAND [options]
  {prog} --examples

OVERVIEW
  {prog} talks to the running Clara window over a per-session local socket.
  It never starts a second GUI. Clara must be running in the same session.
  The socket is user-only (0600); nothing goes over the network.

COMMANDS
  status
      pid, version, mode, project path, unsaved-changes flag, plugin count and uptime.

  show
      Raise the running window.

  save
      Save the open project in place. Fails when no project is open.

  events [-n N] [--tag TAG] [--level LEVEL] [-j]
      Recent log/event history. Default count 50, max 2000.
      --tag      APP, SESSION, PATCHBAY, PLUGIN, CANVAS, SCANNER, ...
      --level    DEBUG, INFO, WARNING, ERROR (DEBUG is hidden by default)
      -j         JSON array

  list <nodes|connections|containers|all> [-j] [--tree] [--full]
      Inspect the canvas.
      nodes       id, kind, name, size, container, port count
      connections cable list as src node:port -> dst node:port
      containers  id, title, layout, member names
      --tree      nest nodes under their containers
      --full      include port names
      -j          JSON

  open <path>
      Open a project in the running window. Refuses if there are unsaved
      changes; save first. If the new load fails, the previous project is
      restored.

  shot [PART] [LOC] [--dialog]
      Save a PNG of the window or a UI region. PART: window (default),
      banner, statusbar, toolbar, context-toolbar, canvas, rack, minimap,
      minimap-map, dialog. LOC may be a file or a directory; with no LOC
      the PNG lands in the current directory. Explicit paths may not be
      symlinks or special files.

  instances [--json]
      List running Clara instances (pid, kind, project, key) so commands can
      target the right one with --instance.

  plugin ui <id> [off]
      Show (or hide) a plugin's custom/native UI window.

  quit [--force]
      Close the window. Refuses while the project has unsaved changes unless
      --force is given (which discards them).

  wait --ready|--dialog [--timeout SECONDS]
      Block until the app has finished starting, or until a dialog is open.
      Use this instead of sleeping before the first command.

  settings open|close|apply|reset|pages
  settings page <name>
  settings fields [<page>] [-j]
  settings get <field>
  settings set <field> <value>
      Drive the open settings dialog. `open` shows it, `set` only changes the
      widget, `apply` commits exactly like the Apply button. `reset` needs
      --force. Fields are the schema ids (app_theme, box_shadows,
      shadow_spread, ...).

  canvas zoom <scale|in|out|fit|reset>
  canvas state [-j]
  canvas select <node ids|all|none>
      Control and inspect the patchbay view; `state` reports zoom, counts and
      the live shadow options. `select` takes comma-separated node ids from
      `list nodes`.

  dialogs [-j]
      List visible dialogs and their button texts.

  dialog accept|cancel|click <text> [--force]
      Act on the active dialog. `click` matches visible button text.
      Destructive texts (discard/delete/remove/erase/overwrite/format/reset/
      quit) are refused without --force.

  replace <node> [--with-plugin <plugin-id> | --with-node <node-id>]
                [--apply | --dry-run] [--no-wait] [-j]
      Replace a node and rewire its cables.
      <node>              node id (first column of `list nodes`)
      --with-plugin ID    use a loaded plugin by plugin id
      --with-node ID      use a loaded node by node id
      no target           opens the plugin browser, then the Rewire dialog
      --dry-run           print the mapping and cable counts; change nothing
      --apply             skip the dialog, use the automatic mapping, wait
      --no-wait           with --apply, return immediately
      Node position, container and color are kept; the old node is removed.
      There is no undo. Save before replacing.

  help
      This help.

IDS
  node id    first column of `list nodes` (the canvas/client id)
  plugin id  plugin_id in `list nodes -j` (the engine slot)
  Ids change after a restart; re-run `list nodes`.

OUTPUT AND EXIT CODES
  Tables by default; -j/--json where supported.
  0 success, 1 failure/not running/unsaved changes, 2 bad usage.

NOTES
  - `carla msg` is rejected; use `clara msg` or `claramsg`.
  - `events` hides DEBUG by default; use `--level debug`.
  - `open` never discards unsaved edits; the GUI asks Save/Discard/Cancel.
  - `replace --apply` waits up to 75 s; `--dry-run` is always safe.
  - screenshots render the patchbay scene, so the GL canvas is included.
"""

_EXAMPLES_TEMPLATE = """{prog} - examples

STATUS AND LOGS
  {prog} status
  {prog} events -n 20
  {prog} events --tag PATCHBAY -n 30
  {prog} events --level debug -n 200
  {prog} events -j | jq .

CANVAS
  {prog} list nodes
  {prog} list nodes --tree
  {prog} list connections
  {prog} list containers -j
  {prog} list all -j

DIALOGS AND SCREENSHOTS
  {prog} dialogs
  {prog} shot
  {prog} instances
  {prog} wait --ready
  {prog} --instance 1234 settings open
  {prog} quit
  {prog} settings open
  {prog} settings page Patchbay
  {prog} settings set shadow_spread 20
  {prog} settings apply
  {prog} canvas zoom 0.5
  {prog} canvas state -j
  {prog} shot ~/Pictures
  {prog} shot --dialog
  {prog} dialog accept
  {prog} dialog cancel
  {prog} dialog click "Replace"
  {prog} dialog click "Discard" --force

PROJECTS
  {prog} open /home/acroarch/Documents/Carla/BusesAndOuts.carjp
  {prog} show

REPLACE
  {prog} replace 31 --with-node 33 --dry-run
  {prog} replace 31 --with-plugin 8 --dry-run
  {prog} replace 31 --with-node 33
  {prog} replace 31 --with-node 33 --apply
  {prog} replace 31 --with-node 33 --apply --no-wait

TIPS
  - `list nodes -j` gives node ids and plugin_id values.
  - Save before replacing; there is no undo.
  - --dry-run changes nothing.
  - --apply waits for the result; --no-wait returns immediately.
"""


_COMMANDS = ("status", "save", "show", "events", "list", "open", "shot", "screenshot",
             "settings", "canvas", "plugin", "rack", "instances", "quit", "wait",
             "dialogs", "dialog", "replace", "help", "examples")


def _use_color():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _paint(text, prog):
    """Colour headings, command names, flags and the tool name."""
    bold, reset = "\x1b[1m", "\x1b[0m"
    cyan, green, blue, magenta = "\x1b[36m", "\x1b[32m", "\x1b[34m", "\x1b[35m"
    text = re.sub(r"(?m)^([A-Z][A-Z0-9 &/]+)$", bold + cyan + r"\1" + reset, text)
    text = re.sub(r"(?m)^  (" + "|".join(_COMMANDS) + r")(?=[ \n])",
                  lambda m: "  " + bold + green + m.group(1) + reset, text)
    text = re.sub(r"(?<![\w-])(--[a-z][\w-]*)", blue + r"\1" + reset, text)
    return re.sub(r"\b" + re.escape(prog) + r"\b", bold + magenta + prog + reset, text)


def print_help(prog="claramsg"):
    text = _HELP_TEMPLATE.format(prog=prog)
    print(_paint(text, prog) if _use_color() else text)


def print_examples(prog="claramsg"):
    text = _EXAMPLES_TEMPLATE.format(prog=prog)
    print(_paint(text, prog) if _use_color() else text)


class _MsgParser(argparse.ArgumentParser):
    """Argparse errors must escape Carla's stderr capture."""

    def error(self, message):
        _emit_error(self.format_usage().rstrip("\n"))
        _emit_error("%s: error: %s" % (self.prog, message))
        raise SystemExit(2)


def _instance_pid(socket_path):
    """Return the pid registered for a socket path, if we know it."""
    from clara_instance_core import list_instances
    for entry in list_instances():
        if entry.get("socket") == socket_path:
            pid = entry.get("pid")
            return pid if isinstance(pid, int) else None
    return None


def _resolve_instance_socket(selector, default_socket):
    """Pick a socket from an --instance selector, or None when it is unknown."""
    if not selector:
        return default_socket
    from clara_instance_core import list_instances
    entries = list_instances()
    selector = str(selector).strip()
    if selector == "latest":
        entries.sort(key=lambda entry: entry.get("started", 0))
        return entries[-1].get("socket") if entries else None
    try:
        wanted_pid = int(selector)
    except ValueError:
        wanted_pid = None
    for entry in entries:
        if wanted_pid is not None and entry.get("pid") == wanted_pid:
            return entry.get("socket")
        if entry.get("key") == selector:
            return entry.get("socket")
    return None


def _screenshot_path(target):
    """Resolve a shot location to an absolute PNG file path."""
    import time
    stamp = time.strftime("clara-shot-%Y%m%d-%H%M%S")
    if not target:
        folder, name = os.getcwd(), stamp + ".png"
    else:
        target = os.path.abspath(os.path.expanduser(str(target)))
        if os.path.isdir(target):
            folder, name = target, stamp + ".png"
        else:
            folder, name = os.path.dirname(target), os.path.basename(target)
            if not name:
                name = stamp + ".png"
    path = os.path.join(folder, name)
    if os.path.exists(path):
        root, ext = os.path.splitext(path)
        index = 2
        while os.path.exists("%s-%d%s" % (root, index, ext)):
            index += 1
        path = "%s-%d%s" % (root, index, ext)
    return path


def run_msg_cli(argv, socket_path, prog="claramsg"):
    parser = _MsgParser(prog=prog, add_help=False)
    parser.add_argument("-h", "--help", action="store_true", dest="show_help",
                        help="show this help")
    parser.add_argument("--examples", action="store_true",
                        help="show copy-paste examples")
    parser.add_argument("--instance", default=None,
                        help="pid, key or 'latest' of the target instance")
    sub = parser.add_subparsers(dest="cmd", parser_class=_MsgParser)
    sub.add_parser("help", help="show this help")
    sub.add_parser("examples", help="show copy-paste examples")
    sub.add_parser("show", help="raise the running window")
    instances_parser = sub.add_parser("instances", help="list running Clara instances")
    instances_parser.add_argument("-j", "--json", action="store_true")
    rack_parser = sub.add_parser("rack", help="inspect rack layout (debug)")
    rack_parser.add_argument("action", nargs="?", default="dump", choices=("dump", "detail"))
    plugin_parser = sub.add_parser("plugin", help="control a plugin")
    plugin_parser.add_argument("action", choices=("ui",))
    plugin_parser.add_argument("plugin_id", type=int)
    plugin_parser.add_argument("value", nargs="?", default=None, help="off to hide")
    quit_parser = sub.add_parser("quit", help="close the window")
    quit_parser.add_argument("--force", action="store_true", help="discard unsaved changes")
    wait_parser = sub.add_parser("wait", help="wait for the app to be ready or show a dialog")
    wait_parser.add_argument("--ready", action="store_true")
    wait_parser.add_argument("--dialog", action="store_true")
    wait_parser.add_argument("--timeout", type=float, default=30.0)
    sub.add_parser("status", help="process and project status")
    sub.add_parser("save", help="save the open project")
    list_parser = sub.add_parser("list", help="inspect the canvas")
    list_parser.add_argument("what", choices=("nodes", "connections", "containers", "all"))
    list_parser.add_argument("-j", "--json", action="store_true", help="raw JSON")
    list_parser.add_argument("--tree", action="store_true", help="nest nodes under containers")
    list_parser.add_argument("--full", action="store_true", help="include port details")

    events_parser = sub.add_parser("events", help="recent log/event history")
    events_parser.add_argument("-n", "--count", type=int, default=50)
    events_parser.add_argument("--tag", default=None)
    events_parser.add_argument("--level", default=None)
    events_parser.add_argument("-j", "--json", action="store_true")

    shot_parser = sub.add_parser("shot", aliases=["screenshot"],
                                 help="save a PNG of the window, a UI region or the active dialog")
    shot_parser.add_argument("part", nargs="?", default="window",
                             help="UI region: window, banner, statusbar, toolbar, "
                                  "context-toolbar, canvas, rack, minimap, dialog")
    shot_parser.add_argument("loc", nargs="?", default=None,
                             help="output file or directory (default: current directory)")
    shot_parser.add_argument("--dialog", action="store_true")
    shot_parser.add_argument("--path", default=None)

    settings_parser = sub.add_parser("settings", help="inspect or drive the settings dialog")
    settings_parser.add_argument("action", choices=(
        "open", "close", "apply", "reset", "pages", "page", "fields", "get", "set"))
    settings_parser.add_argument("target", nargs="?", default=None,
                                 help="page name or field id")
    settings_parser.add_argument("value", nargs="?", default=None, help="value for set")
    settings_parser.add_argument("--force", action="store_true")
    settings_parser.add_argument("-j", "--json", action="store_true")

    canvas_parser = sub.add_parser("canvas", help="control or inspect the patchbay view")
    canvas_parser.add_argument("action", choices=("zoom", "state", "select"))
    canvas_parser.add_argument("value", nargs="?", default=None)
    canvas_parser.add_argument("-j", "--json", action="store_true")

    dialogs_parser = sub.add_parser("dialogs", help="list visible dialogs")
    dialogs_parser.add_argument("-j", "--json", action="store_true")

    dialog_parser = sub.add_parser("dialog", help="act on the active dialog")
    dialog_parser.add_argument("action", choices=("accept", "cancel", "click"))
    dialog_parser.add_argument("text", nargs="?")
    dialog_parser.add_argument("--force", action="store_true", help="allow destructive button text")

    open_parser = sub.add_parser("open", help="open a project in the running window")
    open_parser.add_argument("path")

    replace_parser = sub.add_parser("replace", help="replace a plugin, optionally auto-rewire")
    replace_parser.add_argument("node", type=int)
    replace_parser.add_argument("--with-plugin", dest="other", type=int, default=None,
                                help="plugin id of the replacement")
    replace_parser.add_argument("--with-node", dest="other_node", type=int, default=None,
                                help="node id of the replacement")
    replace_parser.add_argument("--apply", dest="auto", action="store_true",
                                help="apply the auto-mapping without the dialog")
    replace_parser.add_argument("--dry-run", action="store_true")
    replace_parser.add_argument("--no-wait", action="store_true")
    replace_parser.add_argument("-j", "--json", action="store_true")

    args = parser.parse_args(argv)
    if args.examples or args.cmd == "examples":
        print_examples(prog)
        return 0
    if args.show_help or args.cmd == "help" or not args.cmd:
        print_help(prog)
        return 0
    if args.cmd == "instances":
        from clara_instance_core import list_instances
        entries = list_instances()
        if args.json:
            print(json.dumps(entries, indent=2))
        elif not entries:
            print("no running instances")
        else:
            for entry in entries:
                print("%-7s %-7s %-12s %s" % (
                    entry.get("pid", "?"), entry.get("kind", "?"),
                    entry.get("key", "?"), entry.get("project", "")))
        return 0

    socket_path = _resolve_instance_socket(args.instance, socket_path)
    if socket_path is None:
        _emit_error("no such instance: %s" % args.instance)
        return 1

    _ensure_app()

    if args.cmd == "show":
        ok, message = forward_to_primary(socket_path)
        if not ok:
            _emit_error("Clara is not running: %s" % message)
            return 1
        print("OK")
        return 0

    if args.cmd == "events":
        reply = _send(socket_path, build_request(
            "events", count=args.count, tag=args.tag, level=args.level))
        if reply is None:
            return 1
        events = (reply.get("data") or {}).get("events") or []
        if args.json:
            print(json.dumps(events, indent=2))
        else:
            for entry in events:
                print("%s  %-8s %-10s %s" % (
                    entry.get("time", ""), entry.get("level", ""),
                    entry.get("tag", ""), entry.get("message", "")))
        return 0

    if args.cmd in ("shot", "screenshot"):
        payload = build_request("screenshot", dialog=bool(args.dialog),
                                part=args.part)
        payload["path"] = _screenshot_path(args.loc or args.path)
        reply = _send(socket_path, payload)
        if reply is None:
            return 1
        print((reply.get("data") or {}).get("path", ""))
        return 0

    if args.cmd == "plugin":
        reply = _send(socket_path, build_request("plugin", action=args.action,
                                                 plugin=args.plugin_id, value=args.value))
        if reply is None:
            return 1
        data = reply.get("data") or {}
        print("%s %s" % (data.get("name", data.get("plugin")),
                         "shown" if data.get("shown") else "hidden"))
        return 0

    if args.cmd == "rack":
        reply = _send(socket_path, build_request("rack", action=args.action))
        if reply is None:
            return 1
        import json as _json
        print(_json.dumps((reply.get("data") or {}), indent=1))
        return 0

    if args.cmd == "quit":
        reply = _send(socket_path, build_request("quit", force=bool(args.force)))
        if reply is None:
            return 1
        # Wait for the process to actually disappear. Its cleanup unlinks the
        # socket path, so restarting too early can delete the new instance's
        # socket (and lock) from under it.
        pid = _instance_pid(socket_path)
        if pid is not None:
            deadline = time.time() + 10.0
            while time.time() < deadline:
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
                time.sleep(0.1)
        print("OK")
        return 0

    if args.cmd == "wait":
        deadline = time.time() + max(1.0, args.timeout)
        while time.time() < deadline:
            if args.dialog:
                reply = _send(socket_path, build_request("dialogs"))
                if reply is not None and (reply.get("data") or {}).get("dialogs"):
                    print("dialog")
                    return 0
            else:
                reply = _send(socket_path, build_request("status"))
                if reply is not None and (reply.get("data") or {}).get("mode") == "gui":
                    print("ready")
                    return 0
            time.sleep(0.3)
        _emit_error("timed out waiting for %s" % ("a dialog" if args.dialog else "the app"))
        return 1

    if args.cmd == "settings":
        payload = build_request("settings", action=args.action, target=args.target,
                                value=args.value, force=bool(args.force))
        reply = _send(socket_path, payload)
        if reply is None:
            return 1
        data = reply.get("data") or {}
        if args.json:
            print(json.dumps(data, indent=2))
        elif args.action == "pages":
            for page in data.get("pages") or []:
                print("  %s%s" % (page.get("name"), " (hidden)" if page.get("hidden") else ""))
        elif args.action == "fields":
            for field in data.get("fields") or []:
                print("%-26s %-10s %s" % (field.get("id"), field.get("type"), field.get("value")))
        elif args.action == "get":
            print(data.get("value"))
        elif args.action == "set":
            print("%s = %s" % (data.get("field"), data.get("value")))
        elif args.action == "page":
            print(data.get("page"))
        else:
            print("OK")
        return 0

    if args.cmd == "canvas":
        payload = build_request("canvas", action=args.action, value=args.value)
        reply = _send(socket_path, payload)
        if reply is None:
            return 1
        data = reply.get("data") or {}
        if args.json:
            print(json.dumps(data, indent=2))
        elif args.action == "state":
            for key, value in (data.get("canvas") or {}).items():
                print("%-18s %s" % (key, value))
        elif args.action == "select":
            print(data.get("selected"))
        else:
            print(data.get("scale"))
        return 0

    if args.cmd == "dialogs":
        reply = _send(socket_path, build_request("dialogs"))
        if reply is None:
            return 1
        dialogs = (reply.get("data") or {}).get("dialogs") or []
        if args.json:
            print(json.dumps(dialogs, indent=2))
        else:
            if not dialogs:
                print("no visible dialogs")
            for dialog in dialogs:
                print("%s%s" % (
                    dialog.get("title", "(untitled)"),
                    " [modal]" if dialog.get("modal") else ""))
                if dialog.get("buttons"):
                    print("  buttons: " + ", ".join(dialog["buttons"]))
        return 0

    if args.cmd == "dialog":
        payload = build_request("dialog", action=args.action, text=args.text or "", force=bool(args.force))
        reply = _send(socket_path, payload)
        if reply is None:
            return 1
        print(json.dumps(reply.get("data") or {}, indent=2))
        return 0

    if args.cmd == "open":
        reply = _send(socket_path, build_request("open", path=os.path.abspath(args.path)))
        if reply is None:
            return 1
        print("opened")
        return 0

    if args.cmd == "replace":
        if args.other is not None and args.other_node is not None:
            _emit_error("use either --with-plugin or --with-node, not both")
            return 2
        payload = build_request("replace")
        payload["node"] = args.node
        if args.other is not None:
            payload["with"] = args.other
        if args.other_node is not None:
            payload["with_node"] = args.other_node
        payload["auto"] = bool(args.auto)
        payload["dry_run"] = bool(args.dry_run)
        reply = _send(socket_path, payload)
        if reply is None:
            return 1
        data = reply.get("data") or {}
        if args.json:
            print(json.dumps(data, indent=2))
        elif args.dry_run:
            print("dry run: kept %s/%s ports, %s cables preserved, %s dropped" % (
                data.get("kept"), data.get("ports"),
                data.get("cables_kept"), data.get("cables_dropped")))
            for row in data.get("rows") or []:
                print("  %-24s -> %-24s (%s)" % (
                    row.get("old"), row.get("target") or "DROP", row.get("reason")))
        elif args.auto and not args.no_wait:
            deadline = time.monotonic() + 75.0
            while time.monotonic() < deadline:
                status = _send(socket_path, build_request("rewire_status"))
                state = (status or {}).get("data") or {}
                if state.get("done"):
                    if state.get("idle"):
                        print("no rewire job")
                        return 1
                    if state.get("error"):
                        _emit_error("rewire failed: " + str(state.get("error")))
                        return 1
                    print("replaced with %s: kept %s cable(s), dropped %s, failed %s" % (
                        state.get("label", ""), state.get("kept", 0),
                        state.get("dropped", 0), state.get("failed", 0)))
                    return 0
                time.sleep(0.15)
            _emit_error("rewire did not finish in 30s")
            return 1
        else:
            print(json.dumps(data, indent=2) if data else "ok")
        return 0

    if args.cmd == "save":
        reply = _send(socket_path, build_request("save"))
        if reply is None:
            return 1
        print("saved", (reply.get("data") or {}).get("path", ""))
        return 0

    if args.cmd == "status":
        payload = build_request("status")
        raw = MsgClient.request(socket_path, encode_request(payload))
        if raw is None:
            _emit_error("Clara is not running.")
            return 1
        reply = json.loads(raw.decode("utf-8", "replace"))
        if not reply.get("ok"):
            _emit_error((reply.get("error") or {}).get("message", "failed"))
            return 1
        data = reply.get("data") or {}
        for key in ("pid", "version", "code_version", "mode", "project", "dirty", "plugins", "tray", "uptime"):
            value = data.get(key, "")
            if key in ("dirty", "tray") and key in data:
                value = "yes" if value else "no"
            print("%-8s %s" % (key, value))
        return 0

    payload = build_request("list", what=args.what, full=bool(args.full))
    raw = MsgClient.request(socket_path, encode_request(payload))
    if raw is None:
        _emit_error("Clara is not running.")
        return 1
    reply = json.loads(raw.decode("utf-8", "replace"))
    if not reply.get("ok"):
        _emit_error((reply.get("error") or {}).get("message", "failed"))
        return 1
    data = reply.get("data") or {}

    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    if args.what in ("nodes", "all"):
        _print_nodes_table(data, args.tree)
    if args.what in ("connections", "all"):
        _print_connections_table(data)
    if args.what in ("containers", "all"):
        _print_containers_table(data)
    return 0
