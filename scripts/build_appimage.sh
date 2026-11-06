#!/usr/bin/env bash
# ---------------------------------------------------------------------------------------------------------------------
# Clara - portable AppImage builder
#
# Builds a self-contained .AppImage into dist/ for the current ARCH
# (x86_64 or aarch64, selectable with --arch=). The image bundles:
#   * a relocatable CPython (python-build-standalone)
#   * PyQt6 - whose "PyQt6-Qt6" wheel already ships the matching Qt6 libraries
#     and platform plugins, so the AppImage does not depend on the system Qt
#   * the Clara native libs + Python frontend (make install)
#   * remaining non-Qt system libs gathered with linuxdeploy
#
# Only x86_64 and aarch64 asset names are produced; see TODO for other arches.
#
# Everything the script needs that is not already installed is downloaded into
# build/appimage-tools. Network access is required on the first run.
# ---------------------------------------------------------------------------------------------------------------------
set -euo pipefail

# Run the AppImage-format build tools without requiring FUSE (fuse2).
export APPIMAGE_EXTRACT_AND_RUN=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------------------------------------------------
# configuration / arguments

ARCH="${ARCH:-x86_64}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
PYTHON_PBS_VERSION="${PYTHON_PBS_VERSION:-3.12.4}"   # full version of the python-build-standalone asset
PYTHON_PBS_TAG="${PYTHON_PBS_TAG:-20240726}"
PYQT6_VERSION="${PYQT6_VERSION:-6.7.1}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"
NO_BUILD=0
CLEAN=0

for arg in "$@"; do
    case "$arg" in
        --arch=*)   ARCH="${arg#*=}" ;;
        --no-build) NO_BUILD=1 ;;
        --clean)    CLEAN=1 ;;
        -h|--help)
            printf 'Usage: %s [--arch=x86_64] [--no-build] [--clean]\n' "$0"
            exit 0
        ;;
        *) printf 'Unknown argument: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

if [ "$ARCH" != "x86_64" ] && [ "$ARCH" != "aarch64" ]; then
    printf 'ERROR: unsupported --arch=%s (supported: x86_64, aarch64).\n' "$ARCH" >&2
    exit 1
fi

VERSION="$(sed -n 's/^VERSION[[:space:]]*:=[[:space:]]*//p' Makefile | head -n1)"
[ -n "$VERSION" ] || VERSION="0.0.0"

# Clara application version - drives the output file name and AppImage metadata.
# CI overrides this with CLARA_VERSION (derived from the release tag); otherwise
# read CLARA_VERSION_STRING from the frontend, falling back to the engine VERSION.
if [ -z "${CLARA_VERSION:-}" ] || ! printf '%s' "$CLARA_VERSION" | grep -qE '^[0-9]'; then
    CLARA_VERSION="$(sed -n 's/^CLARA_VERSION_STRING[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' source/frontend/carla_shared.py | head -n1)"
fi
[ -n "$CLARA_VERSION" ] || CLARA_VERSION="$VERSION"

OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/dist}"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build/appimage}"
TOOLS_DIR="${TOOLS_DIR:-$REPO_ROOT/build/appimage-tools}"
APPDIR="$BUILD_DIR/Clara.AppDir"
OUTPUT_NAME="Clara-${CLARA_VERSION}-${ARCH}.AppImage"

mkdir -p "$OUTPUT_DIR" "$TOOLS_DIR"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------------------------------------------------
# tool acquisition

download() {
    local url="$1" dest="$2"
    [ -f "$dest" ] && return 0
    log "Downloading $(basename "$dest")"
    if command -v curl >/dev/null 2>&1; then
        curl -fL --retry 3 -o "$dest.part" "$url" && mv "$dest.part" "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$dest.part" "$url" && mv "$dest.part" "$dest"
    else
        die "curl or wget is required to download build tools"
    fi
}

LINUXDEPLOY_BIN=""
APPIMAGETOOL_BIN=""

ensure_linuxdeploy() {
    LINUXDEPLOY_BIN="$TOOLS_DIR/linuxdeploy-${ARCH}.AppImage"
    download "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${ARCH}.AppImage" "$LINUXDEPLOY_BIN"
    chmod +x "$LINUXDEPLOY_BIN"
}

ensure_appimagetool() {
    if command -v appimagetool >/dev/null 2>&1; then
        APPIMAGETOOL_BIN="$(command -v appimagetool)"
    else
        APPIMAGETOOL_BIN="$TOOLS_DIR/appimagetool-${ARCH}.AppImage"
        download "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage" "$APPIMAGETOOL_BIN"
        chmod +x "$APPIMAGETOOL_BIN"
    fi
}

PYTHON_DIR=""
ensure_python() {
    PYTHON_DIR="$TOOLS_DIR/cpython-${PYTHON_PBS_VERSION}-${ARCH}"
    if [ -x "$PYTHON_DIR/bin/python3" ]; then
        return 0
    fi
    local tarball="$TOOLS_DIR/cpython-${PYTHON_PBS_VERSION}-${ARCH}.tar.gz"
    download "https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_PBS_TAG}/cpython-${PYTHON_PBS_VERSION}+${PYTHON_PBS_TAG}-${ARCH}-unknown-linux-gnu-install_only.tar.gz" "$tarball"
    log "Extracting relocatable CPython ${PYTHON_PBS_VERSION} (${ARCH})"
    mkdir -p "$PYTHON_DIR"
    tar -xzf "$tarball" -C "$PYTHON_DIR" --strip-components=1
}

# ---------------------------------------------------------------------------------------------------------------------
# shrink the AppDir
#
# Most of the weight comes from the PyQt6-Qt6 wheel (Qt6 libs) plus the
# relocatable CPython. We drop files that are never used at runtime (dev
# headers, static libs, type stubs, caches, translations, QML, CMake metadata
# and the bundled pip) and strip every ELF we can.

trim_appdir() {
    log "Trimming AppDir (removing dev/doc/cache files, stripping binaries)"

    local pydefs
    pydefs=("$APPDIR"/usr/python/lib/python3.*)

    find "$APPDIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find "$APPDIR" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.pyi' \) -delete 2>/dev/null || true
    find "$APPDIR" -type f \( -name '*.a' -o -name '*.la' -o -name '*.prl' \) -delete 2>/dev/null || true

    for d in "${pydefs[@]}"; do
        rm -rf \
            "$d/test" "$d/idlelib" "$d/tkinter" "$d/turtledemo" "$d/ensurepip" \
            "$d/lib2to3" "$d/pydoc_data" "$d/site-packages/pip" \
            "$d/site-packages/pip-"*.dist-info 2>/dev/null || true
    done

    local pysite
    pysite=( "$APPDIR"/usr/python/lib/python3.*/site-packages/PyQt6/Qt6 )
    for q in "${pysite[@]}"; do
        rm -rf \
            "$q/translations" "$q/qml" \
            "$q/lib/cmake" "$q/lib/pkgconfig" "$q/lib/metatypes" 2>/dev/null || true
    done

    rm -rf "$APPDIR"/usr/include "$APPDIR"/usr/lib/pkgconfig \
           "$APPDIR"/usr/share/man "$APPDIR"/usr/share/doc 2>/dev/null || true

    find "$APPDIR" -type f \( -name '*.so' -o -name '*.so.*' -o -perm -u+x \) \
        -exec sh -c 'file -b "$1" | grep -q ELF' _ {} \; -exec strip --strip-unneeded {} + 2>/dev/null || true
}

# ---------------------------------------------------------------------------------------------------------------------
# build the project

if [ "$CLEAN" = "1" ]; then
    log "Cleaning previous build tree"
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
fi

if [ "$NO_BUILD" != "1" ]; then
    log "Building Clara (DEFAULT_QT=6)"
    make -j"$JOBS" DEFAULT_QT=6
else
    log "Skipping build (--no-build)"
fi

# ---------------------------------------------------------------------------------------------------------------------
# assemble AppDir

log "Assembling AppDir at $APPDIR"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share"

# 1) native libs + frontend + resources via the project's installer
make install DESTDIR="$APPDIR" PREFIX=/usr DEFAULT_QT=6

# 2) relocatable python + PyQt6 (bundles Qt6)
ensure_python
log "Copying CPython into AppDir"
cp -a "$PYTHON_DIR/." "$APPDIR/usr/python/"
BUNDLED_PY="$APPDIR/usr/python/bin/python3"
"$BUNDLED_PY" -m pip install --no-warn-script-location --upgrade pip >/dev/null
log "Installing PyQt6 ${PYQT6_VERSION}"
"$BUNDLED_PY" -m pip install --no-warn-script-location "PyQt6==${PYQT6_VERSION}"

PYQT6_DIR="$("$BUNDLED_PY" -c 'import PyQt6, os; print(os.path.dirname(PyQt6.__file__))')"
QT6_DIR="$PYQT6_DIR/Qt6"

# 3) desktop entry + icons (AppDir root; linuxdeploy/appimagetool want them here)
install -m 644 data/desktop/clara.desktop "$APPDIR/clara.desktop"

ICON_ROOT="$APPDIR/usr/share/icons/hicolor"
for size in 16 32 48 128 256; do
    if [ -f "resources/${size}x${size}/carla.png" ]; then
        mkdir -p "$ICON_ROOT/${size}x${size}/apps"
        install -m 644 "resources/${size}x${size}/carla.png" "$ICON_ROOT/${size}x${size}/apps/carla.png"
    fi
done
if [ -f resources/scalable/carla.svg ]; then
    mkdir -p "$ICON_ROOT/scalable/apps"
    install -m 644 resources/scalable/carla.svg "$ICON_ROOT/scalable/apps/carla.svg"
fi
install -m 644 resources/256x256/carla.png "$APPDIR/carla.png" 2>/dev/null \
    || install -m 644 resources/scalable/carla.svg "$APPDIR/carla.svg"

# ---------------------------------------------------------------------------------------------------------------------
# AppRun

log "Writing AppRun"
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
# Clara AppRun - runs the bundled CPython against the Clara frontend using the
# AppImage-local prefix, and points Qt at the PyQt6-bundled Qt6 plugins/libs.
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/python/bin:$HERE/usr/bin:$PATH"

# PyQt6 ships its own Qt6. Resolve it at runtime relative to the bundled
# Python; never bake the build-machine path into the image.
QT6_DIR="$("$HERE/usr/python/bin/python3" -c 'import PyQt6, os; print(os.path.join(os.path.dirname(PyQt6.__file__), "Qt6"))' 2>/dev/null)"

# Put PyQt6's Qt6 first so a stray system Qt copied by linuxdeploy can never
# shadow it (a version mismatch breaks symbol resolution).
export LD_LIBRARY_PATH="$QT6_DIR/lib:$HERE/usr/lib/carla:$HERE/usr/lib:$LD_LIBRARY_PATH"

# Ensure host PipeWire JACK wrappers (e.g. Fedora / Bazzite / Debian) are discovered
for pwjack_dir in /usr/lib64/pipewire-0.3/jack /usr/lib/pipewire-0.3/jack /usr/lib/x86_64-linux-gnu/pipewire-0.3/jack /usr/lib/aarch64-linux-gnu/pipewire-0.3/jack; do
    if [ -d "$pwjack_dir" ]; then
        export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$pwjack_dir"
    fi
done

export QT_PLUGIN_PATH="$QT6_DIR/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QT6_DIR/plugins/platforms"

exec "$HERE/usr/python/bin/python3" "$HERE/usr/share/carla/carla" \
    --with-appname="$HERE/usr/bin/clara" \
    --with-libprefix="$HERE/usr" \
    "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# In-image launcher; resolve AppRun relative to this script (never the host path).
cat > "$APPDIR/usr/bin/clara" <<'CLARAWRAP'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/../../AppRun" "$@"
CLARAWRAP
chmod +x "$APPDIR/usr/bin/clara"
ln -sf clara "$APPDIR/usr/bin/claramsg"

# ---------------------------------------------------------------------------------------------------------------------
# gather remaining non-Qt dependencies (native libs, jack, sndfile, ...)

ensure_linuxdeploy
ensure_appimagetool

log "Deploying shared-library dependencies"
# Point linuxdeploy at the bundled python and the Carla native libs. Qt is
# intentionally not handled by linuxdeploy-plugin-qt: PyQt6 already ships it.
export LINUXDEPLOY_OUTPUT_VERSION="$CLARA_VERSION"
"$LINUXDEPLOY_BIN" --appdir "$APPDIR" \
    --executable "$APPDIR/usr/python/bin/python3" \
    --desktop-file "$APPDIR/clara.desktop" \
    --icon-file "$APPDIR/carla.png" \
    2>&1 | sed 's/^/    /' || log "linuxdeploy reported issues; continuing"

# Qt6 is provided by PyQt6 (matching version). The Qt-linked native frontend
# (libcarla_frontend) is no longer built or shipped, so linuxdeploy should not
# pull a system Qt anymore; the line below is just a safety net against a stray
# build-host copy.
find "$APPDIR/usr/lib" -maxdepth 1 -name 'libQt6*.so*' -delete 2>/dev/null || true
find "$APPDIR/usr/lib" -maxdepth 1 -name 'libQt5*.so*' -delete 2>/dev/null || true

# ---------------------------------------------------------------------------------------------------------------------
# shrink, then build the AppImage

trim_appdir

log "Building $OUTPUT_NAME"
export ARCH CLARA_VERSION
export VERSION="$CLARA_VERSION"
"$APPIMAGETOOL_BIN" "$APPDIR" "$OUTPUT_DIR/$OUTPUT_NAME" \
    --comp zstd \
    --mksquashfs-opt -Xcompression-level --mksquashfs-opt "${APPIMAGE_ZSTD_LEVEL:-19}"

log "Done: $OUTPUT_DIR/$OUTPUT_NAME"
