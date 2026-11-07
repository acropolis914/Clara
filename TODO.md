# Carla Development Tasks

> **Difficulty Scale**: `[Diff: 1]` Easy / Quick win · `[Diff: 2]` Moderate · `[Diff: 3]` Complex / Architectural

---

## 🔌 Plugin Compatibility
- [x] `[Diff: 2]` **FIX**: sfizz LV2 state no longer depends on Carla's `/tmp/sfizz` symlinks. The patched `sfizz-ui` branch stores raw absolute `sfzfile`/`tuningfile` paths and Carla's bridge restores the saved instrument directly. The compat shim and patched sfizz bundle stay until `sfztools/sfizz-ui#16` lands upstream.
- [x] `[Diff: 2]` **FIX**: bridged LV2 plugins lost project custom data on load. The bridge could run `state:restore` before the custom-data batch, and the old `isEnabled()` guard dropped data while the plugin was still disabled. Custom data now always applies, then one `state:restore` runs after the whole batch; verified with sfizz, 4x LSP Mixer x8 Stereo and LSP Autogain Stereo.
- [ ] `[Diff: 2]` **TEST**: add a regression fixture for bridged LV2 custom state using a non-sfizz plugin (for example LSP Mixer x8 Stereo), so the batch-before-restore ordering stays covered automatically.

## 🐛 Bugs
- [x] `[Diff: 2]` **FIX**: theming was slow and the rack background/outline was hardcoded. The rack list no longer paints its own background or inset frame, the splitter no longer uses the Fusion default line, and the global QSS uses Qt palette roles. A live theme switch previews instantly in the settings dialog and then reapplies the stylesheet to the chrome (~1.2s, rack excluded) instead of two full widget repolishes; rack slots restyle incrementally after the dialog closes. Plugin edit dialogs are built lazily, cutting the widget tree from ~18.8k to ~7.2k.
- [ ] `[Diff: 2]` **THEME AUDIT**: replace the remaining hardcoded hex fallbacks in `carla_skin.py`, `pluginlist/pluginlistdialog_py.py`, `project_dialogs.py`, `update_checker.py` and `canvas_context_toolbar.py` with theme tokens; add a lint check so new widget code cannot introduce color literals.

- [x] `[Diff: 1]` Fix: Rack item remove button still does not delete or show confirmation dialog (reopened: calf skin vs other skins / context menu / delete key)
- [x] `[Diff: 1]` Fix: Left-click drag on empty canvas does not pan the UI
- [x] `[Diff: 1]` Fix: Patchbay canvas node power button (`⏻`) does not toggle plugin processing state reliably
- [x] `[Diff: 1]` Fix: Patchbay canvasbox selected text color is inverted or unreadable against header background
- [ ] `[Diff: 2]` Fix: Nested patchbay sessions get corrupted when a patchbay is opened from inside another patchbay (upstream [falkTX/Carla#1715](https://github.com/falkTX/Carla/issues/1715)) - reported by users, highest priority because it risks project data loss
- [ ] `[Diff: 1]` Triage: High CPU usage reported by users - attribute the load before touching anything (suspect: Yabridge/PipeWire host scanning rather than the Carla engine)
- [ ] `[Diff: 2]` Fix: Focus changes did not refresh cable gradients, so cables kept the previous node colours until the node was moved
- [x] `[Diff: 1]` Fix: Canvas toolbar toggles (signal flow/pulses, grid, snap, pointer/select/hand) looked identical whether enabled or disabled, so the "on" state was invisible
- [x] `[Diff: 1]` Fix: Manually created cables faded in over 750ms, making a new connection feel unresponsive
---

## 🎛️ Patchbay Canvas & Navigation
- [x] `[Diff: 1]` feat: Patchbay selection keyboard shortcuts (Ctrl+A to select all, Photoshop-style selection shortcuts: Ctrl+D to deselect, Ctrl+Shift+I to invert selection)
- [x] `[Diff: 2]` feat: Smoother patchbay rendering and interaction performance (higher refresh/frame rate, reduced dragging jitter and cable render overhead)
- [x] `[Diff: 1]` feat: Search selection persists selected items until user interaction
- [x] `[Diff: 2]` feat: Subtle canvas alignment dots/grid with snapping; align functions respect grid snap
- [x] `[Diff: 2]` feat: Auto repel arrangement tools (auto repel selected vs auto repel all), defaulting auto arrange and auto repel to selected items only
- [x] `[Diff: 3]` feat: Infinite canvas with `infinite-canvas = true` project metadata and migration for legacy files (recenter by subtracting half total bounding box on both X and Y axes)
- [x] `[Diff: 1]` feat: Canvasbox sub-bar action buttons (quick controls/actions bar with Nerd Font icons)
- [x] `[Diff: 2]` feat: Option/checkbox on canvasbox to collapse or hide ports without active connections


---

## 🔗 Cables & Patchbay Visuals
- [x] `[Diff: 2]` feat: Cable routing styles (Bezier, Straight/Linear, Orthogonal/Right-angle)
- [x] `[Diff: 2]` feat: Dynamic cable coloring based on source and destination node colors with linear gradients
- [x] `[Diff: 1]` Fix/feat: Patchbay canvasbox color changes dynamically update connected canvas line gradients immediately without requiring redraw or node moves
- [x] `[Diff: 3]` feat: Visual signal/event flow animations - pulsing/glow animations on active nodes and animated traveling pulses or particles along cables when audio/MIDI events are transmitted
- [x] `[Diff: 2]` Fix: OpenGL-first canvas rendering - default to hardware acceleration, eliminate artificial software-render throttling, fix PulseAudio peak-detect read callback in `pwlevels.py`, and reapply clean UI fixes
- [x] `[Diff: 2]` Fix: Signal-flow pulses sometimes disappear on quiet/transient audio - need peak-hold envelope smoothing so brief silences do not drop a node below the pulse threshold (flicker/stutter)
- [x] `[Diff: 2]` feat: Tint signal-flow glows/pulses with the correct colors along the chain - blend from the source node color through the cable to the destination node color (per-endpoint gradient) instead of the single fixed cyan/white


---

## 🎚️ Rack & Dual-View Integration
- [x] `[Diff: 2]` feat: Side-by-side view for mini rack and patchbay with bidirectional focus/scroll synchronization
- [x] `[Diff: 2]` feat: Synchronized colors, bypass state, and switch button between rack node and patchbay node
- [x] `[Diff: 2]` feat: Minified rack mode exposing only essential controls (Photoshop layer view with mini collapsible slider tray)
- [ ] `[Diff: 2]` feat: A/B Quick-Audition & Snapshot Switching - store two temporary routing/bypass states to toggle between alternative chains with a single hotkey/button

---

## ⚙️ Settings & System UI
- [x] `[Diff: 1]` feat: Settings dialog sidebar enhancement - use a more readable, cohesive font
- [x] `[Diff: 2]` feat: Settings dialog polish & cleanup - reorganize sections, improve layout, use modern compact pills instead of outdated bitmap icons, and add live reactive tweakables
- [x] `[Diff: 1]` feat: Minimize to system tray
- [ ] `[Diff: 2]` Cleanup: the static theme files in `source/frontend/styles/themes/` are unreachable (the theme engine always compiles from `base_primitives.qss`), so their rules never apply - port the useful ones into the engine or delete them

---

## 📊 Status Bar & Diagnostics
- [x] `[Diff: 2]` feat: Reposition/resize bottom bar audio info (sample rate, buffer size, DSP load, etc.) - make flexible and compact for tiling
- [ ] `[Diff: 2]` feat: Mini DSP load graph over time with side label and hover tooltip
- [ ] `[Diff: 2]` feat: Floating sidebar quick settings overlay for patchbay with integrated search bar

---

## 💾 Project Session & System Utilities
- [x] `[Diff: 1]` feat: Offer to save dirty edits on exit (Yes, No, Cancel) with visual save status indicator (dirty/saved)
- [x] `[Diff: 1]` feat: Status indicator for last autosave timestamp and countdown timer to next autosave
- [x] `[Diff: 2]` feat: Improved logging with Python Rich console, loglevels, log tags, and CLI flags (`--log-whitelist`, `--log-blacklist`)
- [ ] `[Diff: 2]` feat: Project notes for current session/save file with rich Markdown rendering support in Qt (QTextDocument markdown / preview)
- [x] `[Diff: 1]` feat: Standardized `argparse` integration to expose all CLI flags and `--help` with Python `rich` formatting
- [x] `[Diff: 1]` feat: Rich CLI startup banner (`Clara vX.Y.Z` / `based on Carla version A.B.C`) and a formatted SIGINT prompt with a safe Enter-to-exit default
- [x] `[Diff: 1]` Fix/feat: Full `.carjp` project file integration across autosave manager, recent files list, dirty tracking, and startup autoload
---

## 🧠 Graph Introspection & Layout
- [x] `[Diff: 2]` feat: Graph introspection model (`collect_graph`) returning JSON-able nodes + ports + connections + derived topology, shared by arrange/control layers

---

## 🕹️ Control Interface (claractl / scripting)
> **Build the ops layer first.** The shared command layer is plain functions over the existing graph-introspection model, so it is usable by the UI on its own and every IPC front-end (CLI, MCP, in-UI scripting) is just a thin transport on top of it. Starting with the socket means designing the protocol before the commands exist.

- [ ] `[Diff: 2]` Shared ops layer as pure functions over the graph-introspection model: `getallnodes`, `getnode`, `getallconnections`, `movenode`, `connect src aport dst bport`, `disconnect`, `arrange`, `setlinestyle`, `getgraph`, `nodesinfo`
- [ ] `[Diff: 3]` IPC core: `QLocalServer` (UNIX socket) started by the GUI (`--control-socket`), newline-delimited JSON request/response protocol (depends on the ops layer)
- [ ] `[Diff: 2]` `claractl` CLI + `carla --getnodeinfo` alias - connect to a running instance, print JSON or tables
- [ ] `[Diff: 3]` In-UI scripting tab - `exec` user code with a `Clara` facade injected into globals (no imports), e.g. `Clara.getAllNodes() -> dict`
- [ ] `[Diff: 2]` MCP/lib wrapper exposing the same ops layer for external agents

---

## 🧩 UI Decoupling & Multi-Framework Architecture (Parked)
- [ ] `[Diff: 3]` Extract Headless Session & Engine Controller: Decouple backend state and event dispatching from `carla_host.py:HostWindow` into a framework-agnostic `SessionController`.
- [ ] `[Diff: 2]` Standardize UI Manifest & Operations API: Implement pure command bus (`core/ops.py`) for pluggable frontends (Transport, Rack, Patchbay, Plugin Browser, Session).
- [ ] `[Diff: 2]` Framework-agnostic Rack and Canvas data models: Decouple `carla_skin.py` and `patchcanvas/` logic from `QWidget` / `QGraphicsItem` hierarchies.
- [ ] `[Diff: 3]` WebSocket / IPC Gateway: Allow alternative modern frontends (Tauri, Slint, Web) to connect and bidirectionally sync with running Clara instances.

---

## 📚 Documentation & Branding
- [x] `[Diff: 1]` docs: Add a "Why Clara?" section to the README (frontend/QoL focus, explicit credit to upstream Carla)
- [x] `[Diff: 1]` docs: Refresh README, installation, and CONTRIBUTING for the v1.1.0 CLI experience
- [x] `[Diff: 1]` docs: Replace long dashes (em/en) with standard punctuation across docs, comments, and CI output

---

## 🚀 Release Engineering & CI
- [x] `[Diff: 2]` CI: Enforce tag/version consistency (`version-check` job, `scripts/check_version.sh`, `pre-push` hook)
- [x] `[Diff: 2]` Fix: Release workflow shallow checkout rejected the AUR `HEAD:main` push (`fetch-depth: 0`)
- [x] `[Diff: 1]` Fix: `release_and_push_aur.sh` now bumps `base_version` alongside the AUR `pkgver`
- [x] `[Diff: 1]` Release: Ship v1.0.4, v1.0.5, and v1.1.0 (bin + source packages, AppImage, Flatpak, Nix)

---

## 📦 Packaging & Distribution
- [x] `[Diff: 1]` Create and maintain `clara-bin` package on AUR for rapid binary installations alongside `clara-git`
- [x] `[Diff: 3]` feat: AppImage build with standalone builder bundling CPython + PyQt6/Qt6
- [x] `[Diff: 2]` feat: Flatpak manifest (`org.kde.Platform` 6.8 runtime) + automated CI workflow
- [x] `[Diff: 1]` Decide Qt bundling policy: bundle libQt6 + PyQt6 inside AppImage/Flatpak for modern system portability
- [x] `[Diff: 1]` Fix: AUR `clara-bin` build aborted with `Dotfile found in package root '.BUILDINFO'` - the release asset is itself a pacman package, so its pacman metadata has to be stripped
- [x] `[Diff: 1]` Fix: AUR source URL was built from `${pkgrel}` while the release assets always use `pkgrel=1`, so bumping the AUR counter broke the download with a 404
- [x] `[Diff: 1]` Fix: makepkg's strip/debug pass produced `gdb-add-index` noise and an empty `clara-bin-debug` split package from the already-stripped release binaries
- [x] `[Diff: 1]` feat: Manual AUR sync workflow, so packaging fixes reach the AUR without waiting for a full release cycle
- [x] `[Diff: 1]` Fix: Release job reset the published AUR `pkgrel` to the repository base value; the counter is now derived from the live AUR package

## 🎛️ Patchbay Canvas & Navigation
- [x] `[Diff: 3]` feat: Group patchbay nodes into containers (VBox, HBox, Grid) with non-destructive backdrop framing, interactive drop zones, and standby reconnect recovery

---

## 🧵 Deferred / Parked by Design

