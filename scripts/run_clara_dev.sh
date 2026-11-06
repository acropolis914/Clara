#!/usr/bin/env bash
# Launch the source build, ensuring no other Carla instance is alive first.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for pattern in 'python3 .*/carla( |$)' 'python3 .*/share/carla/carla( |$)'; do
    for pid in $(pgrep -f "$pattern" || true); do
        kill -9 "$pid" 2>/dev/null || true
    done
done
pkill -f 'carla-bridge-native' 2>/dev/null || true
pkill -x pw-record 2>/dev/null || true
sleep 2

# The fixed socket path is gone; the new build derives a per-session path and
# removes a stale socket itself once it owns the lock.
rm -f "${XDG_RUNTIME_DIR:-/tmp}/carla-standalone.sock"
cd "$ROOT/source/frontend"
exec ./carla "$@"
