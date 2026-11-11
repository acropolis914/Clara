#!/usr/bin/env bash
# Fetches the vendored Lucide icon set into source/frontend/resources/lucide.
#
# The directory is gitignored: icons live on your machine, not in the repo.
# Run this once after a fresh clone, or whenever a new icon name is needed —
# just add the name to ICONS below and rerun.
#
# License: Lucide is ISC; see source/frontend/resources/lucide/LICENSE after
# fetching (this script downloads it too).
set -euo pipefail

VERSION="0.545.0"
BASE="https://unpkg.com/lucide-static@${VERSION}/icons"
DEST="$(dirname "$0")/../source/frontend/resources/lucide"

ICONS=(
  activity arrow-right-left arrow-up-wide-narrow ban bolt boxes box-select brush
  cable chevron-down chevron-up circle-help columns-2 copy eraser external-link
  eye eye-off file-plus file-plus-2 file-x folder folder-open globe grid-3x3 hand
  align-center-horizontal align-center-vertical info lightbulb list list-x log-out magnet maximize maximize-2 menu minus monitor
  mouse-pointer move move-horizontal move-vertical network pencil pin play plus
  power puzzle refresh-cw save save-all settings settings-2 skip-back
  sliders-horizontal skip-forward square square-check toggle-left trash-2
  triangle-alert wine x zoom-in zoom-out
)

mkdir -p "$DEST"
for icon in "${ICONS[@]}"; do
  if [[ -f "$DEST/$icon.svg" ]]; then
    continue
  fi
  if ! aria2c -q -d "$DEST" -o "$icon.svg" "$BASE/$icon.svg"; then
    echo "missing upstream: $icon" >&2
  fi
done

aria2c -q -d "$DEST" -o LICENSE "https://unpkg.com/lucide-static@${VERSION}/LICENSE"
echo "Lucide icons in $DEST: $(ls "$DEST"/*.svg 2>/dev/null | wc -l)"
