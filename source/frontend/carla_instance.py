#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Clara single-instance lock + local control channel (Qt).
# The lock is the source of truth; the socket is only the transport.

import argparse
import json
import os
import sys
import time

from qt_compat import (
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

try:
    from PyQt6.QtCore import QCoreApplication
except ImportError:
    from PyQt5.QtCore import QCoreApplication


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
    return reply


def run_msg_cli(argv, socket_path):
    _ensure_app()
    parser = argparse.ArgumentParser(prog="clara msg", add_help=True)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("show", help="raise the running window")
    sub.add_parser("status", help="process and project status")
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

    shot_parser = sub.add_parser("screenshot", help="save a PNG of the window or active dialog")
    shot_parser.add_argument("--dialog", action="store_true")
    shot_parser.add_argument("--path", default=None)

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
    replace_parser.add_argument("--apply", dest="auto", action="store_true", help="apply the auto-mapping without the dialog")
    replace_parser.add_argument("--dry-run", action="store_true")
    replace_parser.add_argument("--no-wait", action="store_true")
    replace_parser.add_argument("-j", "--json", action="store_true")

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 2

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
                print("%s [%-5s] [%s] %s" % (
                    entry.get("time", ""), entry.get("level", ""),
                    entry.get("tag", ""), entry.get("message", "")))
        return 0

    if args.cmd == "screenshot":
        payload = build_request("screenshot", dialog=bool(args.dialog))
        if args.path:
            payload["path"] = args.path
        reply = _send(socket_path, payload)
        if reply is None:
            return 1
        print((reply.get("data") or {}).get("path", ""))
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
        for key in ("pid", "version", "mode", "project", "plugins", "uptime"):
            print("%-8s %s" % (key, data.get(key, "")))
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
