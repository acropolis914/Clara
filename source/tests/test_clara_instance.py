#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Pure (no Qt) tests for the single-instance identity and control protocol.

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

import clara_instance_core as core


def test_paths_are_stable_and_private():
    paths = core.instance_paths()
    assert paths["key"]
    assert paths["lock"].endswith(".lock")
    assert paths["socket"]
    if os.name != "nt":
        assert paths["socket"].endswith(".sock")
        assert "/clara-" in paths["lock"]
    assert core.instance_paths()["key"] == paths["key"]


def test_instance_key_override():
    old = os.environ.get("CLARA_INSTANCE_KEY")
    try:
        os.environ["CLARA_INSTANCE_KEY"] = "dev-key"
        assert core.instance_key() == "dev-key"
    finally:
        if old is None:
            os.environ.pop("CLARA_INSTANCE_KEY", None)
        else:
            os.environ["CLARA_INSTANCE_KEY"] = old


def test_invocation_names():
    assert core.is_clara_invocation("clara")
    assert core.is_clara_invocation("/usr/bin/clara")
    assert not core.is_clara_invocation("carla")
    assert not core.is_clara_invocation("")


def test_first_positional_skips_wrapper_options():
    argv = ["--with-appname=/usr/bin/clara", "--with-libprefix=/usr", "msg", "list", "nodes"]
    assert core.first_positional(argv) == "msg"
    assert core.first_positional(["--debug", "debug", "/tmp/p.carjp"]) == "/tmp/p.carjp"
    assert core.first_positional(["-n"]) is None


def test_legacy_show():
    request = core.decode_request(b"SHOW")
    assert request["cmd"] == "show" and request["legacy"]


def test_json_roundtrip():
    request = core.build_request("list", what="nodes", full=False)
    decoded = core.decode_request(core.encode_request(request))
    assert decoded["cmd"] == "list" and decoded["what"] == "nodes"
    reply = core.encode_reply(core.build_reply(True, {"nodes": []}))
    assert json.loads(reply.decode("utf-8"))["ok"] is True


def test_bad_requests():
    for raw in (b"not json", b"{}", b'{"cmd": 1}', b'{"v": 99, "cmd": "list"}'):
        try:
            core.decode_request(raw)
        except core.ProtocolError:
            continue
        raise AssertionError("accepted bad request: %r" % raw)


def test_error_reply_shape():
    reply = core.error_reply("bad_request", "nope")
    assert reply["ok"] is False
    assert reply["error"]["code"] == "bad_request"


def main():
    test_paths_are_stable_and_private()
    test_instance_key_override()
    test_invocation_names()
    test_first_positional_skips_wrapper_options()
    test_legacy_show()
    test_json_roundtrip()
    test_bad_requests()
    test_error_reply_shape()
    print("clara_instance: all checks passed")


if __name__ == "__main__":
    main()
