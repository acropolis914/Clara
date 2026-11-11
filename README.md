> [!IMPORTANT]
> ### Early Alpha - Action Required: Report Bugs & Join Development
> **Clara is evolving rapidly.** While the audio engine, routing graph, and autosaving core are rock-solid, expect UI quirks and experimental behaviors in the patchbay toolbars.
> - **Report Every Bug**: If you encounter crashes, graphical glitches, or broken controls, you **must [open a bug report](https://github.com/acropolis914/Clara/issues/new?template=bug_report.md)** with complete logs and system specs.
> - **Help Build Clara**: We need developers, audio hackers, and maintainers. **[Read CONTRIBUTING.md](CONTRIBUTING.md) and start contributing today.**
> - **Support the Developer**: A dollar goes a long way. I am a student working on my free hours to do this. My allowance doesn't really cut it and it is deeply appreciated if you would support through [**GitHub Sponsors**](https://github.com/sponsors/acropolis914) or [**PayPal**](https://paypal.me/paulharveysuarnaba). Thank you so much!




<div align="center">

# Clara

### Modern, fluid, and safe modular audio plugin host

[![Platform](https://img.shields.io/badge/platform-Linux-313244.svg?style=flat-square&logo=linux&logoColor=cdd6f4)]()
[![License](https://img.shields.io/badge/license-GPLv2%2B-a6e3a1.svg?style=flat-square&logoColor=11111b)](LICENSE)
[![Release](https://img.shields.io/github/v/release/acropolis914/Clara?style=flat-square&color=fab387)](https://github.com/acropolis914/Clara/releases)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%99%A5-f38ba8.svg?style=flat-square&logo=githubsponsors&logoColor=11111b)](https://github.com/sponsors/acropolis914)
[![Upstream](https://img.shields.io/badge/upstream-falkTX%2FCarla-cba6f7.svg?style=flat-square)](https://github.com/falkTX/Carla)


<br/>

<img src="resources/screenshots/image.png?raw=true&v=2" alt="Clara Patchbay & Rack Screenshot" width="880" style="border-radius: 8px;" />

<br/>

[Why Clara?](#why-clara) &bull;
[Key Features](#key-features) &bull;
[Quick Start & Packages](#installation--packages) &bull;
[Building from Source](#building-from-source) &bull;
[Roadmap](#roadmap) &bull;
[Contributing](CONTRIBUTING.md) &bull;
[Ideas & Suggestions](SUGGESTIONS.md) &bull;
[Upstream Features](#upstream-features)


<br/>

</div>

---

## About Clara

**Clara** (*Carla Improved*) is an enhanced fork of [Carla](https://github.com/falkTX/Carla) by [falkTX](https://github.com/falkTX). It modernizes modular audio routing on Linux by delivering fluid canvas navigation, automatic session preservation, deep dual-view integration, and high-DPI visuals designed for audio engineers and electronic music performers.

> [!NOTE]
> **Early Alpha Status**: Clara is in active, rapid development. Core audio routing, plugin hosting, session autosaving, and everyday workflows are fully functional and ready for daily use. Feedback and bug reports are welcome!

---

## Why Clara?

**First, credit where it is due:** [Carla](https://github.com/falkTX/Carla) is the OG: a rock-solid, battle-tested modular plugin host by [falkTX](https://github.com/falkTX) that has powered Linux audio for years. Clara does not replace that engine; it stands on Carla's shoulders, and everything you rely on (plugin hosting, drivers, stability) is still Carla underneath.

Clara is a **frontend-first reinterpretation** of that foundation, focused on **visuals and quality-of-life**. The engine is kept up to date with upstream, while the experience around it was reworked: the plugin scanner and loader got a pass, alongside general optimizations, some cleanup, and **OpenGL enabled by default** to drive the animations.

The goal is simple: an **eye-candy patchbay that asks for fewer clicks**.

- **Arrange & align**: auto-arrange, arrange in rows, multi-select with align, auto-repel when nodes overlap, and line nodes up before or after each other.
- **Less clicking in the graph**: direct bypass and switch buttons on the patchbay node, plus hiding I/O ports that are not in use.
- **Make it yours**: toggleable rounded node corners and a toggleable split-screen view (patchbay beside the rack, in lockstep).

If you already know Carla, Clara should feel familiar in all the right places and fresh everywhere you look.

---

## The Modern Modular Experience

Carla's rock-solid audio backend, supercharged with modern creative-suite ergonomics, intelligent graph layouts, and clean visual polish:
<img src="resources/screenshots/gradient_cables.png?raw=true&v=2" alt="Clara Patchbay & Rack Screenshot" width="880" style="border-radius: 8px;" />
- **Real-Time Color Sync & Gradient Cables**
  - One-click Catppuccin palette or custom color wheel: changing a color on any node **instantly syncs** across the canvas box, its rack module, and all connected cables.
  - Connection cables render as **smooth directional linear gradients**, seamlessly interpolating from the source node's accent into the destination node's tone.
- **Clean, Focused & Contemporary Aesthetic**
  - Stripped of retro clutter: enjoy **4x MSAA hardware acceleration**, rounded card geometry, high-contrast category badges (`SYNTH`, `FX`, `HW`, `IN`/`OUT`), and crystal-clear hinted typography.
  - Floating context-aware icon toolbars keep controls within reach while leaving your graph completely unobstructed.
- **Creative-Suite Selection & Navigation**
  - **Photoshop & Blender Muscle Memory**: `Space` or `H` to glide across your infinite canvas, `V` for precise interaction, and `Q` for rubberband marquee.
  - **Directional Marquee Selection**: Drag left-to-right to select touched nodes; drag right-to-left for strict bounding box enclosure.
  - **Pro Selection Shortcuts**: `Ctrl+A` (Select All), `Ctrl+D` (Deselect All), and `Ctrl+Shift+I` (Invert Selection).
  - **`Ctrl+F` Fuzzy Search**: Instantly spotlight and camera-jump to any plugin or port in seconds across complex multi-client setups.
- **Smart Auto-Arrange & Collision-Free Alignment**
  - Effortless cleanup: automatically untangle sprawling routing webs with **repel-aware auto-arrange** that respects node boundaries and prevents overlapping collisions.
  - Align selected nodes horizontally or vertically with uniform spacing at the click of a button.
- **Dual-View Power: Patchbay + Rack in Lockstep**
  - Graph routing meets knob tweaking: view the modular patchbay alongside the mini rack in a seamless side-by-side split.
  - **Bidirectional Focus Lock**: Clicking any node in the patchbay instantly scrolls and focuses its rack panel, and vice versa.
- **Zero-Anxiety Session Preservation**
  - Background rotating autosaves (`.autosaves/`), modified dirty indicators (`*`), live status countdown timers, and safe-exit verification dialogs ensure you never lose a creative take.
- **Live Dynamic Customization (Zero Restarts)**
  - Tailor Clara to your display on the fly with live responsive sliders for rack margins, slot padding, and layout width.

---

## Key Features

### Modern Patchbay Canvas & Navigation
- **Photoshop/Blender Modal Tools**: Instant hotkeys (`V` Select/Move, `H`/`Space` Pan, `Q` Marquee) with a floating tool overlay.
- **Canvas Node Quick Search (`Ctrl+F`)**: Fuzzy search bar that automatically filters, highlights, and centers viewport onto target nodes.
- **Selection Ergonomics**: Industry-standard shortcuts (`Ctrl+A`, `Ctrl+D`, `Ctrl+Shift+I`) and multi-selection preservation across context menus.
- **Fluid & Crisp Rendering**: Native 4x MSAA multisampling on OpenGL viewports with subpixel integer hinting for ultra-sharp port labels.

### Vibrant Theming & Cable Routing
- **Unified Catppuccin Colors**: Automatic color-coding by audio role (`SYNTH`, `FX`, `EQ`, `DYN`, `UTIL`, `SOURCE`, `SINK`, `HW`).
- **Dynamic Cable Gradients**: Connection cables smoothly interpolate source and destination node colors via linear gradients.
- **Configurable Cable Formulas**: Choose between organic Bezier curves, straight/linear diagonals, or orthogonal right-angle routing.

### Side-by-Side Dual-View Workflow
- **Rack & Graph Synchronization**: Split dual-pane combining modular routing with parameter tweaking.
- **Bidirectional Focus**: Clicking any patchbay node instantly scrolls and highlights its corresponding rack module, and vice versa.

### Session Safety & Fault Tolerance
- **Automatic Rotating Autosaves**: Background rotating backups (`.autosaves/`) with recursive directory guard.
- **Dirty State Tracking**: Real-time modified indicator (`*`) and status bar countdown timer until the next autosave snapshot.
- **Safe Exit Protection**: Confirmation prompt (`Save`, `Discard`, `Cancel`) when closing modified sessions.

### Rich Console Logging & Live UI Tweaks
- **Structured Python Rich Console**: Color-coded loglevels and categorical tags (`APP`, `ENGINE`, `PATCHBAY`, `BACKEND`) with low-level C++ `stderr` interception.
- **Instant Reactive Settings**: Real-time sliders for rack spacing, padding, and width without application restarts.

### Modern CLI Experience
- **Rich Startup Banner**: Launching from a terminal renders a `rich` panel reading `Clara vX.Y.Z` then `based on Carla version A.B.C`, alongside the runtime and binary/resource paths; `--version` shows the same banner.
- **Graceful Ctrl+C Handling**: The terminal SIGINT prompt is a `rich` panel where pressing `Enter` quits (default) and `T` keeps Clara running in the system tray.

---

## Installation & Packages

Pre-built binaries are provided for major Linux distributions:

| Distribution | Format | Quick Installation |
| :--- | :--- | :--- |
| **Any Linux (x86_64)** | AppImage | `chmod +x Clara-*-x86_64.AppImage && ./Clara-*-x86_64.AppImage` |
| **Any Linux (Flatpak)** | Flatpak | `flatpak install --user Clara-*-x86_64.flatpak` |
| **Arch Linux** | AUR / Pacman | `paru -S clara-bin` or `clara-git` (see [`aur/`](aur/)) |
| **Ubuntu / Debian** | `.deb` | `sudo dpkg -i clara-ubuntu-*.deb && sudo apt-get install -f` |
| **Fedora / RHEL** | `.rpm` | `sudo dnf install clara-*.rpm` |
| **Void Linux** | `.tar.zst` | Extract to `/` (`tar --zstd -xvf clara-void-*.tar.zst -C /`) |
| **Alpine Linux** | `.tar.zst` | Extract to `/` (`tar --zstd -xvf clara-alpine-*.tar.zst -C /`) |
| **Nix / NixOS** | Flake | `nix run github:acropolis914/Clara` |

> The standalone **AppImage** bundles its own Python + PyQt6/Qt6, so it runs on modern distributions without installing anything. The **Flatpak** uses the `org.kde.Platform` runtime. The primary binary and desktop entry are named **`clara`**; **`carla`** is kept as a backwards-compatible symlink.

[**Browse Release Tags & Assets**](https://github.com/acropolis914/Clara/releases)

---

## Building from Source

### Quick Build Script
```bash
./build.sh
```

### Manual Build
```bash
# Compile backend & UI resources
make -j$(nproc)

# Run Clara directly from source tree
./bin/carla
```

Refer to [`installation.md`](installation.md) for full distribution-specific build dependencies.

---

## Roadmap

Active task tracking and architectural priorities are maintained in [TODO.md](TODO.md).

**Recently shipped:**
- [x] Rich CLI startup banner and a safe SIGINT exit prompt.
- [x] Visual audio/MIDI signal activity animations along cables and active nodes.
- [x] Infinite canvas with migration recentering for legacy projects.
- [x] Standardized `argparse` CLI integration with `rich` help output.
- [x] Release pipeline hardening: tag/version consistency guard and AUR publish fix.
- [x] Patchbay focus fixes: the focused node title stays readable, and cables react to focus immediately.
- [x] AUR packaging fixes: `clara-bin` builds and installs again, and packaging fixes can be published without a full release.
- [x] Patchbay toolbar feedback: enabled toggles are highlighted in the theme accent, and new cables are drawn instantly.
- [x] Window lifecycle & tray fixes: plugin edit window close no longer shuts down engine, and minimize-to-tray handles Wayland compositors cleanly.

**Next up:**
- [ ] Shared ops layer for graph control (`getallnodes`, `connect`, `arrange`, `getgraph`), as the base for every front-end.
- [ ] `claractl` CLI / IPC core for live graph control and scripting.
- [ ] Mini DSP load history graph with side labels and hover tooltips.
- [ ] In-project session notes with rich Qt Markdown (`QTextDocument`) preview.
- [ ] Floating sidebar quick settings overlay with integrated search.

---

## Join the Project: We're Looking for Contributors & Maintainers!

> [!TIP]
> **Help Shape the Future of Linux Modular Audio!**
> Whether you're an experienced C++/Qt hacker, a Python developer, a DSP audio nerd, a UI/UX designer, or an everyday music producer finding edge-case bugs: **we want your help.**

Clara is evolving fast, and we are actively looking for:
- **Core Developers & Co-Maintainers**: Help refine the canvas architecture, Qt6 modernize legacy modules, and review PRs.
- **UI/UX & Theme Designers**: Polish vector icons, refine high-DPI skins, and elevate graph interaction ergonomics.
- **Testers & Bug Hunters**: Put large multi-client JACK/PipeWire routing setups through their paces and report crashes/regressions.

Check out our current backlog in [**TODO.md**](TODO.md) for open tasks rated by difficulty (`[Diff: 1]` to `[Diff: 3]`).

### AI-Assisted Development Policy
- **Guided AI Usage is Permitted**: Contributors are allowed to use AI coding agents and assistants, such as **Google Antigravity / Gemini**, Claude, or Copilot, to research, scaffold, refactor, and draft code.
- **Explicit AI Disclosure Required**: If AI was used in any part of creating a PR, you **must explicitly state so in the PR description**, noting the tools used and the prompts/intent.
- **Rigorous Quality Review**: AI-generated code will not be accepted without scrutiny. All PRs are **extensively reviewed for architectural sanity, clean code standards, Qt compatibility, and stability**. Contributors must test and take full ownership of their submitted code.
- Read [**CONTRIBUTING.md**](CONTRIBUTING.md) for build guides, coding standards, and PR submission checklist.


---

## Upstream Features

Clara retains complete support for all native Carla host capabilities:
- **Plugin Formats**: LADSPA, DSSI, LV2, VST2, VST3, CLAP, and AU plugins.
- **Sound Banks**: SF2/3 and SFZ sound bank playback.
- **Drivers**: Native ALSA, DirectSound, CoreAudio, PulseAudio, and JACK/PipeWire drivers.
- **Automation & MIDI**: Internal MIDI player, MIDI CC parameter automation, and OSC remote control.

Refer to the [upstream Carla website](https://kx.studio/Applications:Carla) for base engine documentation.

---

## Thanks & Credits

Clara stands on the shoulders of a great ecosystem:

- **[falkTX](https://github.com/falkTX)** and the upstream **[Carla](https://github.com/falkTX/Carla)** project — Clara's audio engine, plugin hosting core and OSC surface are built on Carla. Original author of the codebase.
- **[Lucide](https://lucide.dev)** — the icon set used across the UI. ISC license, vendored via `scripts/fetch-lucide.sh`.
- **[Catppuccin](https://github.com/catppuccin/catppuccin)** — the pastel palettes behind the default themes (Macchiato, Mocha, Latte & friends).
- **The plugin ecosystems** that make a host worth using: the LSP plugin suite, sfizz, Cardinal, Dexed, Helm, u-he, and every LADSPA/LV2/VST/CLAP developer whose work loads inside Clara.
- **Everyone who reports bugs, tests large routing setups, and hangs out in the issue tracker** — an early-alpha project lives on your reports.

---

<div align="center">
  <sub>Maintained by <a href="https://github.com/acropolis914">acropolis914</a>. Original Carla host by <a href="https://github.com/falkTX">falkTX</a>.</sub>
</div>
