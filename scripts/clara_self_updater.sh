#!/usr/bin/env bash
# Clara One-Click Interactive Terminal Updater
# SPDX-License-Identifier: GPL-2.0-or-later

set -e

# ANSI styling
BOLD="\033[1m"
GREEN="\033[1;32m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
MAGENTA="\033[1;35m"
RESET="\033[0m"

TARGET_VERSION="${1:-}"
CURRENT_VERSION="${2:-}"

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║             ${BOLD}✨ CLARA INTERACTIVE UPDATER ✨${RESET}${CYAN}            ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# 1. Fetch release metadata if version is not explicitly passed
RELEASES_URL="https://raw.githubusercontent.com/acropolis914/Clara/main/releases.json"

fetch_releases() {
    if command -v curl >/dev/null 2>&1; then
        curl -sSL "$RELEASES_URL" 2>/dev/null || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$RELEASES_URL" 2>/dev/null || true
    fi
}

if [ -z "$TARGET_VERSION" ]; then
    echo -e "${BLUE}ℹ Fetching latest release information...${RESET}"
    LATEST_INFO=$(fetch_releases)
    TARGET_VERSION=$(echo "$LATEST_INFO" | grep -o '"latest": *"[^"]*"' | head -n1 | cut -d'"' -f4)
fi

[ -z "$TARGET_VERSION" ] && TARGET_VERSION="latest"

# The version can come from the network feed; refuse anything but a dotted number (or "latest").
if [ "$TARGET_VERSION" != "latest" ] && ! printf '%s' "$TARGET_VERSION" | grep -Eq '^[0-9]+(\.[0-9]+)*$'; then
    echo "Invalid version: $TARGET_VERSION" >&2
    exit 1
fi

if [ -z "$CURRENT_VERSION" ]; then
    # Try to detect installed version
    if command -v clara >/dev/null 2>&1; then
        CURRENT_VERSION=$(clara --version 2>&1 | grep -oP 'Clara v\K[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    elif command -v carla >/dev/null 2>&1; then
        CURRENT_VERSION=$(carla --version 2>&1 | grep -oP 'Clara v\K[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    fi
fi

echo -e "${BLUE}Current version:${RESET} ${YELLOW}v${CURRENT_VERSION:-unknown}${RESET}"
echo -e "${BLUE}Target version:${RESET}  ${GREEN}v${TARGET_VERSION}${RESET}"
echo ""

# 2. Detect installation method and Distribution Family
INSTALL_METHOD=""
DISTRO_FAMILY=""

# Detect installation method first (package manager provenance)
CLARA_BIN_PATH="$(command -v clara 2>/dev/null || command -v carla 2>/dev/null || true)"
if [ -n "$CLARA_BIN_PATH" ]; then
    # Check if it's a Flatpak
    if [[ "$CLARA_BIN_PATH" == *"/app/"* ]] || [ -n "${FLATPAK_ID:-}" ] || command -v flatpak >/dev/null 2>&1 && flatpak list --app 2>/dev/null | grep -q "Clara"; then
        INSTALL_METHOD="flatpak"
    # Check if it's an AppImage
    elif [ -n "${APPIMAGE:-}" ] || [[ "$(readlink -f "$CLARA_BIN_PATH" 2>/dev/null || echo "$CLARA_BIN_PATH")" == *".AppImage"* ]]; then
        INSTALL_METHOD="appimage"
    # Check package manager ownership
    elif command -v dpkg >/dev/null 2>&1 && dpkg -S "$CLARA_BIN_PATH" >/dev/null 2>&1; then
        INSTALL_METHOD="deb"
        DISTRO_FAMILY="ubuntu"
    elif command -v pacman >/dev/null 2>&1 && pacman -Qo "$CLARA_BIN_PATH" >/dev/null 2>&1; then
        INSTALL_METHOD="arch"
        DISTRO_FAMILY="arch"
    elif command -v rpm >/dev/null 2>&1 && rpm -qf "$CLARA_BIN_PATH" >/dev/null 2>&1; then
        PKG_NAME=$(rpm -qf "$CLARA_BIN_PATH" 2>/dev/null | head -1)
        if [[ "$PKG_NAME" =~ clara ]]; then
            INSTALL_METHOD="rpm"
            DISTRO_FAMILY="fedora"
        fi
    elif command -v apk >/dev/null 2>&1 && apk info -e "${PKG_NAME:-}" >/dev/null 2>&1; then
        INSTALL_METHOD="apk"
        DISTRO_FAMILY="alpine"
    elif command -v xbps-query >/dev/null 2>&1 && xbps-query -f "$CLARA_BIN_PATH" >/dev/null 2>&1; then
        INSTALL_METHOD="xbps"
        DISTRO_FAMILY="void"
    fi
fi

# Fallback to distro detection if install method not determined
if [ -z "$DISTRO_FAMILY" ] && [ -f /etc/os-release ]; then
    . /etc/os-release
    ID_LIKE_LOWER=$(echo "${ID_LIKE:-}" | tr '[:upper:]' '[:lower:]')
    ID_LOWER=$(echo "${ID:-}" | tr '[:upper:]' '[:lower:]')

    if [[ "$ID_LOWER" =~ (arch|manjaro|endeavouros|garuda|cachyos|artix) ]] || [[ "$ID_LIKE_LOWER" =~ arch ]]; then
        DISTRO_FAMILY="arch"
        [ -z "$INSTALL_METHOD" ] && INSTALL_METHOD="arch"
    elif [[ "$ID_LOWER" =~ (ubuntu|debian|pop|mint|elementary|kali|zorin) ]] || [[ "$ID_LIKE_LOWER" =~ (debian|ubuntu) ]]; then
        DISTRO_FAMILY="ubuntu"
        [ -z "$INSTALL_METHOD" ] && INSTALL_METHOD="deb"
    elif [[ "$ID_LOWER" =~ (fedora|rhel|centos|rocky|almalinux|nobara) ]] || [[ "$ID_LIKE_LOWER" =~ (fedora|rhel) ]]; then
        DISTRO_FAMILY="fedora"
        [ -z "$INSTALL_METHOD" ] && INSTALL_METHOD="rpm"
    elif [[ "$ID_LOWER" =~ void ]]; then
        DISTRO_FAMILY="void"
        [ -z "$INSTALL_METHOD" ] && INSTALL_METHOD="xbps"
    elif [[ "$ID_LOWER" =~ alpine ]]; then
        DISTRO_FAMILY="alpine"
        [ -z "$INSTALL_METHOD" ] && INSTALL_METHOD="apk"
    elif [[ "$ID_LOWER" =~ nixos ]] || [ -d "/nix" ]; then
        DISTRO_FAMILY="nix"
        [ -z "$INSTALL_METHOD" ] && INSTALL_METHOD="nix"
    fi
fi

# 3. Interactive fallback picker if detection fails or user wants to override
prompt_picker() {
    echo -e "${YELLOW}Could not automatically determine how Clara was installed.${RESET}"
    echo -e "Please select your installation method:"
    echo -e "  ${BOLD}1)${RESET} Arch Linux / AUR (paru / yay / pacman) - ${MAGENTA}clara-bin/clara-git${RESET}"
    echo -e "  ${BOLD}2)${RESET} Ubuntu / Debian (.deb via apt/dpkg)"
    echo -e "  ${BOLD}3)${RESET} Fedora / RHEL (.rpm via dnf)"
    echo -e "  ${BOLD}4)${RESET} Void Linux (xbps / tarball)"
    echo -e "  ${BOLD}5)${RESET} Alpine Linux (apk / tarball)"
    echo -e "  ${BOLD}6)${RESET} Nix / NixOS"
    echo -e "  ${BOLD}7)${RESET} Flatpak"
    echo -e "  ${BOLD}8)${RESET} AppImage"
    echo -e "  ${BOLD}9)${RESET} Manual tarball install"
    read -rp "Enter choice [1-9]: " choice
    case "$choice" in
        1) DISTRO_FAMILY="arch"; INSTALL_METHOD="arch" ;;
        2) DISTRO_FAMILY="ubuntu"; INSTALL_METHOD="deb" ;;
        3) DISTRO_FAMILY="fedora"; INSTALL_METHOD="rpm" ;;
        4) DISTRO_FAMILY="void"; INSTALL_METHOD="xbps" ;;
        5) DISTRO_FAMILY="alpine"; INSTALL_METHOD="apk" ;;
        6) DISTRO_FAMILY="nix"; INSTALL_METHOD="nix" ;;
        7) INSTALL_METHOD="flatpak" ;;
        8) INSTALL_METHOD="appimage" ;;
        9) INSTALL_METHOD="tarball" ;;
        *) echo -e "${RED}Invalid selection. Aborting.${RESET}"; exit 1 ;;
    esac
}

if [ -z "$INSTALL_METHOD" ]; then
    prompt_picker
fi

echo -e "${BLUE}Installation method:${RESET} ${MAGENTA}${INSTALL_METHOD}${RESET} ${DISTRO_FAMILY:+($DISTRO_FAMILY)}"
echo ""

# Helper to execute privileged command via pkexec or sudo
run_privileged() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    elif command -v pkexec >/dev/null 2>&1; then
        pkexec "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo -e "${RED}Error: Neither pkexec nor sudo is available to execute root operations.${RESET}"
        exit 1
    fi
}

TMP_DIR=$(mktemp -d /tmp/clara-update-XXXXXX)
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

find_release_asset() {
    local ext_regex="$1"
    local asset_url=""
    if command -v curl >/dev/null 2>&1; then
        asset_url=$(curl -sSL "https://api.github.com/repos/acropolis914/Clara/releases/tags/v${TARGET_VERSION}" 2>/dev/null | grep -o '"browser_download_url": *"[^"]*"' | cut -d'"' -f4 | grep -E "$ext_regex" | head -n 1)
    fi
    echo "$asset_url"
}

# 4. Perform package installation per installation method
case "$INSTALL_METHOD" in
    arch)
        echo -e "${CYAN}→ Updating via Arch package manager (mirroring original install)...${RESET}"
        if command -v paru >/dev/null 2>&1; then
            echo -e "${BLUE}Using paru...${RESET}"
            paru -S --noconfirm clara-git || paru -S --noconfirm clara-bin || {
                echo -e "${YELLOW}Falling back to direct package download...${RESET}"
                PKG_NAME="clara-archlinux-x86_64.tar.zst"
                DOWNLOAD_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
                curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$DOWNLOAD_URL"
                run_privileged tar --zstd -xvf "$TMP_DIR/${PKG_NAME}" -C /
            }
        elif command -v yay >/dev/null 2>&1; then
            echo -e "${BLUE}Using yay...${RESET}"
            yay -S --noconfirm clara-git || yay -S --noconfirm clara-bin || {
                echo -e "${YELLOW}Falling back to direct package download...${RESET}"
                PKG_NAME="clara-archlinux-x86_64.tar.zst"
                DOWNLOAD_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
                curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$DOWNLOAD_URL"
                run_privileged tar --zstd -xvf "$TMP_DIR/${PKG_NAME}" -C /
            }
        elif command -v pacman >/dev/null 2>&1; then
            echo -e "${BLUE}Using pacman...${RESET}"
            # Try to update from repos/AUR if configured, else download
            if pacman -Ss clara 2>/dev/null | grep -q clara; then
                run_privileged pacman -S --noconfirm clara-bin || run_privileged pacman -S --noconfirm clara-git
            else
                echo -e "${YELLOW}Not in repos, downloading direct package...${RESET}"
                PKG_NAME="clara-archlinux-x86_64.tar.zst"
                DOWNLOAD_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
                curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$DOWNLOAD_URL"
                run_privileged tar --zstd -xvf "$TMP_DIR/${PKG_NAME}" -C /
            fi
        else
            echo -e "${YELLOW}No pacman found. Downloading direct release package from GitHub...${RESET}"
            PKG_NAME="clara-archlinux-x86_64.tar.zst"
            DOWNLOAD_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
            curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$DOWNLOAD_URL"
            run_privileged tar --zstd -xvf "$TMP_DIR/${PKG_NAME}" -C /
        fi
        ;;

    deb|ubuntu)
        echo -e "${CYAN}→ Updating via apt/dpkg (mirroring original install)...${RESET}"
        DEB_NAME="clara-ubuntu-x86_64.deb"
        DEB_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${DEB_NAME}"
        echo -e "${BLUE}Downloading ${DEB_NAME}...${RESET}"
        curl -sSL "$DEB_URL" -o "$TMP_DIR/${DEB_NAME}" || wget -qO "$TMP_DIR/${DEB_NAME}" "$DEB_URL"
        echo -e "${CYAN}→ Installing package with dpkg and resolving dependencies with apt...${RESET}"
        run_privileged dpkg -i "$TMP_DIR/${DEB_NAME}" || true
        if command -v apt-get >/dev/null 2>&1; then
            run_privileged apt-get install -f -y
        fi
        ;;

    rpm|fedora)
        echo -e "${CYAN}→ Updating via dnf/rpm (mirroring original install)...${RESET}"
        RPM_URL=$(find_release_asset '\.fc[0-9]+\.x86_64\.rpm$|\.rpm$')
        if [ -n "$RPM_URL" ]; then
            RPM_NAME=$(basename "$RPM_URL")
        else
            RPM_NAME="clara-${TARGET_VERSION}-1.fc44.x86_64.rpm"
            RPM_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${RPM_NAME}"
        fi
        echo -e "${BLUE}Downloading ${RPM_NAME}...${RESET}"
        curl -sSLf "$RPM_URL" -o "$TMP_DIR/${RPM_NAME}" || wget -qO "$TMP_DIR/${RPM_NAME}" "$RPM_URL" || {
            RPM_NAME="clara-fedora-x86_64.rpm"
            RPM_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${RPM_NAME}"
            curl -sSLf "$RPM_URL" -o "$TMP_DIR/${RPM_NAME}" || wget -qO "$TMP_DIR/${RPM_NAME}" "$RPM_URL"
        }
        if command -v dnf >/dev/null 2>&1; then
            echo -e "${CYAN}→ Installing with dnf...${RESET}"
            run_privileged dnf install -y "$TMP_DIR/${RPM_NAME}"
        elif command -v yum >/dev/null 2>&1; then
            echo -e "${CYAN}→ Installing with yum...${RESET}"
            run_privileged yum localinstall -y "$TMP_DIR/${RPM_NAME}"
        else
            echo -e "${CYAN}→ Installing with rpm...${RESET}"
            run_privileged rpm -Uvh "$TMP_DIR/${RPM_NAME}" || run_privileged rpm -ivh --replacepkgs "$TMP_DIR/${RPM_NAME}"
        fi
        ;;

    xbps|void)
        echo -e "${CYAN}→ Updating via xbps/tarball (mirroring original install)...${RESET}"
        VOID_NAME="clara-void-x86_64.tar.zst"
        VOID_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${VOID_NAME}"
        curl -sSL "$VOID_URL" -o "$TMP_DIR/${VOID_NAME}" || wget -qO "$TMP_DIR/${VOID_NAME}" "$VOID_URL"
        echo -e "${CYAN}→ Extracting package to system root...${RESET}"
        run_privileged tar --zstd -xvf "$TMP_DIR/${VOID_NAME}" -C /
        ;;

    apk|alpine)
        echo -e "${CYAN}→ Updating via apk/tarball (mirroring original install)...${RESET}"
        ALPINE_NAME="clara-alpine-x86_64.tar.zst"
        ALPINE_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${ALPINE_NAME}"
        curl -sSL "$ALPINE_URL" -o "$TMP_DIR/${ALPINE_NAME}" || wget -qO "$TMP_DIR/${ALPINE_NAME}" "$ALPINE_URL"
        echo -e "${CYAN}→ Extracting package to system root...${RESET}"
        run_privileged tar --zstd -xvf "$TMP_DIR/${ALPINE_NAME}" -C /
        ;;

    nix)
        echo -e "${CYAN}→ Updating via Nix profile (mirroring original install)...${RESET}"
        if [ "$TARGET_VERSION" = "latest" ] || [ -z "$TARGET_VERSION" ]; then
            nix profile install --upgrade "github:acropolis914/Clara" || nix profile upgrade "github:acropolis914/Clara" || nix profile install --upgrade github:acropolis914/Clara
        else
            nix profile install --upgrade "github:acropolis914/Clara/v${TARGET_VERSION}" || nix profile install --upgrade github:acropolis914/Clara
        fi
        ;;

    flatpak)
        echo -e "${CYAN}→ Updating via Flatpak (mirroring original install)...${RESET}"
        if command -v flatpak >/dev/null 2>&1; then
            # Try to update the Clara app if installed
            flatpak update -y com.github.acropolis914.Clara 2>/dev/null || {
                echo -e "${YELLOW}Clara not found as Flatpak app, or update failed.${RESET}"
                echo -e "${BLUE}Downloading latest Flatpak bundle...${RESET}"
                FLATPAK_NAME="Clara-${TARGET_VERSION}-x86_64.flatpak"
                FLATPAK_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${FLATPAK_NAME}"
                curl -sSL "$FLATPAK_URL" -o "$TMP_DIR/${FLATPAK_NAME}" || wget -qO "$TMP_DIR/${FLATPAK_NAME}" "$FLATPAK_URL"
                flatpak install --user -y "$TMP_DIR/${FLATPAK_NAME}" || flatpak install -y "$TMP_DIR/${FLATPAK_NAME}"
            }
        else
            echo -e "${RED}Flatpak not installed. Please install Flatpak first.${RESET}"
            exit 1
        fi
        ;;

    appimage)
        echo -e "${CYAN}→ Updating AppImage (mirroring original install)...${RESET}"
        APPIMAGE_NAME="Clara-${TARGET_VERSION}-x86_64.AppImage"
        APPIMAGE_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${APPIMAGE_NAME}"
        echo -e "${BLUE}Downloading ${APPIMAGE_NAME}...${RESET}"
        curl -sSL "$APPIMAGE_URL" -o "$TMP_DIR/${APPIMAGE_NAME}" || wget -qO "$TMP_DIR/${APPIMAGE_NAME}" "$APPIMAGE_URL"
        chmod +x "$TMP_DIR/${APPIMAGE_NAME}"
        echo ""
        echo -e "${YELLOW}AppImage downloaded to:${RESET} $TMP_DIR/${APPIMAGE_NAME}"
        echo -e "${BLUE}If you have Clara as a system AppImage, replace the existing one with this file.${RESET}"
        if [ -n "${APPIMAGE:-}" ] && [ -f "${APPIMAGE}" ]; then
            echo -e "${CYAN}→ Your current AppImage is: ${APPIMAGE}${RESET}"
            echo -e "${YELLOW}Run:${RESET} cp \"$TMP_DIR/${APPIMAGE_NAME}\" \"${APPIMAGE}\" && chmod +x \"${APPIMAGE}\""
        fi
        echo -e "${YELLOW}Or move it to your preferred location and make it executable.${RESET}"
        ;;

    tarball)
        echo -e "${CYAN}→ Updating via tarball install (mirroring original install)...${RESET}"
        # Try to guess which tarball format based on system
        if command -v pacman >/dev/null 2>&1; then
            PKG_NAME="clara-archlinux-x86_64.tar.zst"
        elif command -v dpkg >/dev/null 2>&1; then
            PKG_NAME="clara-ubuntu-x86_64.deb"
            DEB_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
            curl -sSL "$DEB_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$DEB_URL"
            run_privileged dpkg -i "$TMP_DIR/${PKG_NAME}" || run_privileged apt-get install -f -y
            echo ""
            echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
            echo -e "${GREEN}✓ Installed. Press enter to exit, please restart Clara${RESET}"
            echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
            read -r
            exit 0
        elif command -v dnf >/dev/null 2>&1 || command -v rpm >/dev/null 2>&1; then
            RPM_URL=$(find_release_asset '\.fc[0-9]+\.x86_64\.rpm$|\.rpm$')
            if [ -n "$RPM_URL" ]; then
                PKG_NAME=$(basename "$RPM_URL")
            else
                PKG_NAME="clara-${TARGET_VERSION}-1.fc44.x86_64.rpm"
                RPM_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
            fi
            curl -sSLf "$RPM_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$RPM_URL" || {
                PKG_NAME="clara-fedora-x86_64.rpm"
                RPM_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
                curl -sSLf "$RPM_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$RPM_URL"
            }
            if command -v dnf >/dev/null 2>&1; then
                run_privileged dnf install -y "$TMP_DIR/${PKG_NAME}"
            elif command -v yum >/dev/null 2>&1; then
                run_privileged yum localinstall -y "$TMP_DIR/${PKG_NAME}"
            else
                run_privileged rpm -Uvh "$TMP_DIR/${PKG_NAME}"
            fi
            echo ""
            echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
            echo -e "${GREEN}✓ Installed. Press enter to exit, please restart Clara${RESET}"
            echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
            read -r
            exit 0
        elif [ -f /etc/alpine-release ]; then
            PKG_NAME="clara-alpine-x86_64.tar.zst"
        elif [ -f /etc/void-release ] || command -v xbps-query >/dev/null 2>&1; then
            PKG_NAME="clara-void-x86_64.tar.zst"
        else
            # Default to AppImage or generic
            echo -e "${YELLOW}Downloading AppImage as fallback...${RESET}"
            APPIMAGE_NAME="Clara-${TARGET_VERSION}-x86_64.AppImage"
            APPIMAGE_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${APPIMAGE_NAME}"
            curl -sSL "$APPIMAGE_URL" -o "$TMP_DIR/${APPIMAGE_NAME}" || wget -qO "$TMP_DIR/${APPIMAGE_NAME}" "$APPIMAGE_URL"
            chmod +x "$TMP_DIR/${APPIMAGE_NAME}"
            echo -e "${YELLOW}AppImage downloaded to:${RESET} $TMP_DIR/${APPIMAGE_NAME}"
            echo ""
            echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
            echo -e "${GREEN}✓ Downloaded. Press enter to exit, please restart Clara${RESET}"
            echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
            read -r
            exit 0
        fi
        DOWNLOAD_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/${PKG_NAME}"
        curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/${PKG_NAME}" || wget -qO "$TMP_DIR/${PKG_NAME}" "$DOWNLOAD_URL"
        echo -e "${CYAN}→ Extracting package to system root...${RESET}"
        run_privileged tar --zstd -xvf "$TMP_DIR/${PKG_NAME}" -C /
        ;;
esac

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}✓ Installed. Press enter to exit, please restart Clara${RESET}"
echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
read -r
