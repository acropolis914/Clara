#!/usr/bin/env bash
# Launch the source build, stopping any running instance first.
# Refuses to kill a session with unsaved changes unless CLARA_DEV_FORCE=1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/source/frontend"

running="$(pgrep -f 'python3 .*/carla( |$)' | head -n1 || true)"
if [ -n "$running" ]; then
    dirty="$(./claramsg list nodes -j 2>/dev/null \
        | python3 -c 'import json, sys; print("1" if json.load(sys.stdin).get("project", {}).get("dirty") else "0")' \
        2>/dev/null || true)"
    if [ "${CLARA_DEV_FORCE:-0}" != "1" ] && [ "$dirty" != "0" ]; then
        echo "Clara has unsaved changes (or its state is unknown); not killing it." >&2
        echo "Save the project, then run this again. Set CLARA_DEV_FORCE=1 to discard them." >&2
        exit 1
    fi
fi

patterns=('python3 .*/carla( |$)' 'python3 .*/share/carla/carla( |$)')
for pattern in "${patterns[@]}"; do
    for pid in $(pgrep -f "$pattern" || true); do
        kill "$pid" 2>/dev/null || true
    done
done
for _ in $(seq 1 20); do
    pgrep -f 'python3 .*/carla( |$)' >/dev/null 2>&1 || break
    sleep 0.25
done
for pattern in "${patterns[@]}"; do
    for pid in $(pgrep -f "$pattern" || true); do
        kill -9 "$pid" 2>/dev/null || true
    done
done
pkill -f 'carla-bridge-native' 2>/dev/null || true
pkill -x pw-record 2>/dev/null || true
sleep 1

# The per-session lock and socket clean themselves up on exit.
exec ./carla "$@"
