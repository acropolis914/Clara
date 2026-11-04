#!/usr/bin/env bash
# Compiles and runs the Carla JSON project document round-trip test.
# No build tree required: water is compiled straight from source.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

g++ -std=c++11 -Wall \
    -I "$ROOT/source/includes" \
    -I "$ROOT/source/modules" \
    -I "$ROOT/source/modules/distrho" \
    -I "$ROOT/source/utils" \
    "$ROOT/source/tests/test-json-document.cpp" \
    "$ROOT/source/modules/water/water.cpp" \
    -pthread \
    -o "$OUT/test-json-document"

"$OUT/test-json-document"
