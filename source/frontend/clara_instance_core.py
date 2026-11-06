#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Clara single-instance identity + control-channel protocol.
# Pure stdlib: safe to import and test without Qt.

import hashlib
import json
import os
import tempfile


PROTOCOL_VERSION = 1
DEFAULT_APP_ID = "clara"
MAX_REQUEST_BYTES = 64 * 1024
MAX_REPLY_BYTES = 8 * 1024 * 1024


class ProtocolError(Exception):
    def __init__(self, code, message):
        super(ProtocolError, self).__init__(message)
        self.code = code
        self.message = message


def session_key():
    """Per graphical session, so a second login gets its own instance."""
    for name in ("XDG_SESSION_ID", "WAYLAND_DISPLAY", "DISPLAY"):
        value = os.environ.get(name)
        if value:
            return "%s=%s" % (name, value)
    return "session=default"


def instance_key(app_id=DEFAULT_APP_ID):
    override = os.environ.get("CLARA_INSTANCE_KEY")
    if override:
        return override
    uid = os.getuid() if hasattr(os, "getuid") else os.environ.get("USERNAME", "user")
    raw = "%s|%s|%s" % (app_id, uid, session_key())
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def runtime_dir():
    """Short, user-private, local directory. XDG on Linux, temp elsewhere."""
    base = os.environ.get("XDG_RUNTIME_DIR")
    if base and os.path.isdir(base):
        return base
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base and os.path.isdir(base):
            return base
    return tempfile.gettempdir()


def instance_paths(app_id=DEFAULT_APP_ID):
    key = instance_key(app_id=app_id)
    base = runtime_dir()
    lock = os.path.join(base, "clara-%s.lock" % key)
    if os.name == "nt":
        # QLocalServer treats a bare name as a named pipe.
        socket_path = "clara-%s" % key
    else:
        socket_path = os.path.join(base, "clara-%s.sock" % key)
    legacy = os.environ.get("CARLA_SINGLE_INSTANCE_SOCKET")
    if legacy:
        socket_path = legacy
    return {"key": key, "base": base, "lock": lock, "socket": socket_path}


def legacy_socket_path():
    """Old fixed socket path, used only to hand over from a pre-lock build."""
    return os.path.join(runtime_dir(), "carla-standalone.sock")


def is_clara_invocation(name):
    """True when the launcher is the Clara name, not plain Carla."""
    return os.path.basename(name or "") == "clara"


def first_positional(argv):
    """First non-option argument, skipping values of known options."""
    value_options = {
        "--cnprefix", "--log-level", "--log-whitelist", "--log-blacklist",
        "--log", "--debug", "--with-appname", "--with-libprefix", "--osc-gui",
    }
    skip = False
    for arg in argv:
        if skip:
            skip = False
            continue
        if arg in value_options:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def build_request(cmd, **fields):
    request = {"v": PROTOCOL_VERSION, "cmd": cmd}
    request.update(fields)
    return request


def encode_request(request):
    return json.dumps(request, separators=(",", ":")).encode("utf-8") + b"\n"


def decode_request(raw):
    """Returns a request dict. Raises ProtocolError on bad input."""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", "replace")
    else:
        text = raw or ""
    text = text.strip()
    if not text:
        return {"v": 0, "cmd": "show", "legacy": True}
    if not text.startswith("{"):
        if text.upper() == "SHOW":
            return {"v": 0, "cmd": "show", "legacy": True}
        raise ProtocolError("bad_request", "expected a JSON request or SHOW")
    try:
        request = json.loads(text)
    except ValueError:
        raise ProtocolError("bad_request", "invalid JSON")
    if not isinstance(request, dict):
        raise ProtocolError("bad_request", "request must be an object")
    cmd = request.get("cmd")
    if not isinstance(cmd, str) or not cmd:
        raise ProtocolError("bad_request", "missing cmd")
    version = request.get("v", PROTOCOL_VERSION)
    if not isinstance(version, int) or version < 1:
        raise ProtocolError("bad_request", "invalid protocol version")
    if version > PROTOCOL_VERSION:
        raise ProtocolError("unsupported", "protocol version %i is newer" % version)
    return request


def build_reply(ok, data=None, error=None):
    reply = {"v": PROTOCOL_VERSION, "ok": bool(ok)}
    if data is not None:
        reply["data"] = data
    if error:
        reply["error"] = error
    return reply


def encode_reply(reply):
    return json.dumps(reply, separators=(",", ":")).encode("utf-8") + b"\n"


def error_reply(code, message):
    return build_reply(False, error={"code": code, "message": message})
