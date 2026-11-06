#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Qt-backed instance tests. Skips when PyQt / QtNetwork is not installed.

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

try:
    from PyQt6.QtCore import QCoreApplication
except ImportError:
    try:
        from PyQt5.QtCore import QCoreApplication
    except ImportError:
        QCoreApplication = None

try:
    import carla_instance
    from carla_instance import InstanceLock, MsgClient, MsgServer
    from clara_instance_core import build_request, encode_request
except Exception as exc:  # pragma: no cover - CI without PyQt
    print("instance_qt: skipped (%s)" % exc)
    sys.exit(0)

if QCoreApplication is None:  # pragma: no cover
    print("instance_qt: skipped (no Qt)")
    sys.exit(0)

_app = QCoreApplication.instance() or QCoreApplication([])


def _handler(request):
    if request.get("cmd") == "list":
        return {"v": 1, "ok": True, "data": {"nodes": [], "containers": [], "connections": []}}
    return {"v": 1, "ok": True, "data": {"echo": request.get("cmd")}}


def test_server_client(tmp):
    socket_path = os.path.join(tmp, "clara-test.sock")
    server = MsgServer(socket_path, _handler)
    assert server.start(remove_stale=True)

    reply = MsgClient.request(socket_path, b"SHOW", 1500)
    assert reply == b"OK", reply

    payload = encode_request(build_request("list", what="nodes"))
    reply = json.loads(MsgClient.request(socket_path, payload, 1500).decode("utf-8"))
    assert reply["ok"] is True and "nodes" in reply["data"]

    payload = encode_request(build_request("nope"))
    reply = json.loads(MsgClient.request(socket_path, payload, 1500).decode("utf-8"))
    assert reply["ok"] is True  # handler-level unknown is the host's job

    server.close()


def test_lock_contention(tmp):
    lock_path = os.path.join(tmp, "clara-test.lock")
    lock = InstanceLock(lock_path)
    assert lock.acquire()
    assert not InstanceLock(lock_path).acquire()
    lock.release()
    lock2 = InstanceLock(lock_path)
    assert lock2.acquire()
    lock2.release()


def test_cross_process_single_winner(tmp):
    lock_path = os.path.join(tmp, "clara-race.lock")
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from carla_instance import InstanceLock;"
        "lock = InstanceLock(%r);"
        "print('won' if lock.acquire() else 'lost');"
        "import time; time.sleep(0.25)"
    ) % (os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"), lock_path)

    procs = [
        subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for _ in range(8)
    ]
    results = []
    for proc in procs:
        out, _err = proc.communicate(timeout=20)
        results.append(out.decode("utf-8").strip())
    assert results.count("won") == 1, results


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_server_client(tmp)
        test_lock_contention(tmp)
        test_cross_process_single_winner(tmp)
    print("instance_qt: all checks passed")


if __name__ == "__main__":
    main()
