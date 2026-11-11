# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Overview

**Clara** (*Carla Improved*) key highlights:
- **Modal Navigation**: Photoshop/Blender hotkeys (`V`, `H`, `Space`, `Q`), infinite canvas, directional marquee box selection, and minimap tracking.
- **Dynamic Cable Gradients & Routing**: Source-to-destination color gradients with Bezier, straight, and stepped routing formulas.
- **Catppuccin Theming**: Automatic category colors, role badges (`SOURCE`, `SINK`, `HW`), and quick popup color swatches.
- **Unified Toolbars**: Floating palettes with standardized Nerd Font glyphs, batch mute/bypass, and alignment/repel tools.
- **Rack & Patchbay Sync**: Side-by-side view with bidirectional scroll, focus, and color synchronization.
- **Session Safety**: Rotating autosaves (`.autosaves/`), countdown timers, dirty edit tracking, and save-on-exit prompts.
- **Rich Diagnostics**: Terminal logs with Python `rich` formatting, color tags, and C++ backend `stderr` capture.

---


## [Unreleased]

### Added

#### 2026-11-11 — Everforest themes

- **chore(ui)**: sunset the legacy `ProjectLoadingDialog` - the class survives only as the renamed `ProjectSessionOfferDialog` (the "Recent Session"/"Recover Session" prompt with its Load/Skip buttons and autoload checkbox); all of its loading/progress mode is deleted. Loading UI is exclusively `InlineLoadingBanner`, including the engine cancelable-action callback which previously spawned the old dialog. Guards added so a non-banner `fLoadingDialog` (the offer prompt) cannot receive `setProgress`.
- **feat(ui)**: scrollbars use the theme accent (soft tint at rest, full accent on hover), and the plugin loading banner got the accent treatment too - fixed its stylesheet selector (the QFrame rule never matched the QWidget), and the progress chunk now shimmers with a moving accent gradient so progress is obvious even when the percent barely moves. Also fixed a constructor-order bug that crashed the banner into the old dialog fallback.
- **fix(ui)**: minimap state restore is now observable - the creation, placement mode, restore values (visible/collapsed/dock/position) and final sizes are logged under the CANVAS tag, plus the collapsed-state transition. This chased down a crash where the dock signal was assigned as an instance attribute (never bound) and killed the overlay creation silently.
- **feat(theming)**: surface elevation pass in the theme engine - `bg-surface`/`bg-hover` are pushed apart from the background semantically (lighter in dark themes, darker in light), so the UI stops reading as one flat shade while staying theme-agnostic.
- **feat(ui)**: minimap gets a visible menu button (floating next to the grip; right-click still works) that opens dock/zoom/hide options; the floating buttons survive the collapsed state on the small overlay chip, and the map always opens with its layout-driven size instead of stale geometry.
- **feat(ui)**: canvas minimap rework — the grip/collapse header row is gone; the buttons now float inside the map's top corners with an offset (they stay translucent and raised above the map's pan/zoom handlers), and the map is dockable via its right-click menu: "Dock at top of rack" / "Dock at bottom of rack" / "Float over canvas". Docking restructures the rack frame into a vertical layout and reparents the map; the choice persists ("Minimap/Dock").
- **feat(ui)**: patchbay toolbar tiles are borderless; when a tool is toggled on, the icon ink inverts against the highlight fill via `contrast_on_highlight()` (theme background token, with a luminance-based black/white fallback), so checked tools stay readable in dark and light themes.
- **feat(ui)**: ten UI polish enhancements: themed tooltips, hover border on rack slots, pointer/hand cursors on knobs/LEDs/sliders, keyboard focus rings, per-pixel rack scrolling, empty states (rack and node search), Lucide icons in canvas context menus (arrange/wire/repel, container layout, group), double-click affordance tooltips on slot titles, tooltips on the LED slice tiles and meters, and a 150ms color crossfade on the LED traffic lights.

- **feat(tests)**: `test_polish_contract.py` — asserts that after theme polish, every pinned widget renders exactly the size its code requested and no widget ends with minimum above maximum. This is the systematic guard for the QSS-overrides-setFixedSize bug class (toolbar buttons, dial, search field all regressed through it).
- **feat(tests)**: the rack layout harness now also asserts every slot's polished minimum height fits its fixed height and its minimum width fits the rack viewport; fixing the exposed offender: the plugin badge label drove ~60px of hidden minimum width in every slot (minimums dropped 281→222px).
- **feat(msg)**: `claramsg status` now reports a `code_version` stamp (newest frontend .py mtime) and `claramsg` warns loudly whenever the running instance predates the code on disk - stale-code debugging no longer masquerades as broken fixes.
- **fix(ui)**: regression from the minimum-width work — the title/badge labels used an `Ignored` size policy which collapsed the whole title stack to zero width next to the stretch spacer, leaving rack slots with no labels. They now keep their natural size hint (Preferred) with an explicit 1px minimum, so they shrink via elision but always render.
- **fix(theming)**: `ThemeEngine.resolve_tokens()` derives the mode from the theme definition when the argument is omitted, instead of silently applying the "dark" default and inverting light themes.
- **fix(ui)**: removed arbitrary width floors that kept rack slots from shrinking to narrow viewports: knobs column (120px floor), rename edit (80px floor), plugin badge label, and tightened the header row spacing.

- **feat(theming)**: new builtin themes "Everforest Dark" and "Everforest Light" (by sainnhe, MIT), using the exact medium-variant palettes from the upstream source; they flow through the standard Base16 pipeline (tokens, QSS, rack skins, patchbay) with the everforest blue `#7fbbb3` / `#3a94c5` as the app accent.

#### 2026-11-11 — Lucide icon set

- **fix(ui)**: canvas toolbar buttons are truly square — the theme QSS box model was overriding `setFixedSize` and squashing them to 28x~22; the scoped toolbar rules now pin equal min/max width and height (26x26 vertical toolbar, 24x24 context toolbar).
- **fix(ui)**: the context toolbar's search field was clipped by the bar — the global `QLineEdit` rule (min-height 22px + padding) polished the field to ~30px tall inside a 32px bar; a scoped rule now keeps it at 24px with tighter padding.
- **fix(ui)**: the canvas context toolbar can never leave the canvas — the search field is shrinkable (120-170px) so a narrow viewport compresses it instead of overflowing the bar, and a user-dragged bar position is now clamped inside the canvas on every reposition (window resizes used to leave it stranded outside).
- **fix(ui)**: the canvas node search results list appeared at wrong coordinates — it was mapped into the graphics view's viewport from the search field in the context toolbar, which is a *sibling*, not a descendant; mapping now goes through global coordinates (drag-proof), and the results list got theme styling (base fill, mid border, rounded items) matching the menus. The context toolbar itself is now a pure box-model autolayout: children sizes are authoritative and the bar follows its layout hint, clamped to the viewport width.
- **fix(ui)**: the canvas context toolbar's layout no longer breaks during load — its width was hand-computed from hardcoded child sizes (26px buttons, label widths from the old bold font) that no longer match the QSS-enforced tiles; the bar is now sized from its own layout (children + QSS are authoritative) and buttons match the 24px tiles.
- **feat(ui)**: the main window toolbar now follows the compact Win11 command-bar look — normal-weight 12px text beside 16px icons, flat transparent buttons with 4px rounded hovers, hairline separators, no border under the bar, fixed 16px icon size.
- **feat(ui)**: the main window toolbar got proper scaling and spacing — scoped QToolBar rules give it a base background with a mid border, consistent 13px text with 16px icons, even paddings and separators, hover/pressed/checked states (was unstyled Qt default: cramped, uneven text/icon scale). Context toolbar section labels ("CANVAS", group/node headers) are now small letter-spaced muted caps instead of a large bold font next to the icon tiles.
- **feat(ui)**: canvas toolbar buttons (vertical toolbar and context toolbar) render as square tile containers — filled with the base palette, a `mid` border and rounded corners — instead of floating transparent icons; hover/checked states unchanged.
- **feat(ui)**: menubar, transport and disk buttons always get icons from the app's own Lucide set. The icons were previously only applied when "Use system theme icons" was enabled (which was off by default, leaving menus iconless); the block is now unconditional.

- **feat(ui)**: all UI icons now come from [Lucide](https://lucide.dev) (ISC), replacing the FontAwesome/Nerd-Font glyph texts and FreeDesktop theme icon lookups: rack slot header buttons (power, bypass, custom UI, edit, slider-mode, minimize chevron), canvas toolbar, canvas context toolbar, canvas node action buttons, settings dialog sidebar and path buttons, minimap collapse, and every menu/toolbar icon routed through `getIcon()` (theme names mapped to Lucide in `widgets/lucide.py`, theme icons remain the fallback when the vendored set is absent).
- **feat(build)**: Lucide SVGs are vendored locally and gitignored; `scripts/fetch-lucide.sh` fetches the pinned set (add an icon name and rerun). Icons load with `stroke="currentColor"` recolored to the active theme palette, so they follow light/dark themes.
- **docs**: About dialog and README credit Lucide, Catppuccin, upstream Carla and plugin ecosystem; new README "Thanks & Credits" section.

#### 2026-11-11 — Exit confirmation and UI regression harness

- **fix(ui)**: quitting never prompts when the exit is programmatic — `shouldIgnoreClose` now returns immediately when `fForceQuit` is set (claramsg quit, tray quit, SIGINT handling), so a non-interactive exit no longer spawns the "Are you sure you want to quit Carla?" dialog. The redundant clean-quit confirmation is also off by default now (`Main/ConfirmExit` defaults to false); the Save/Discard/Cancel prompt for unsaved changes remains and covers data safety.
- **feat(tests)**: `source/tests/test_rack_layout.py` — a UI regression harness that launches a real Clara instance headless (PulseAudio driver, isolated QSettings, offscreen platform, its own instance key), loads the rack fixture project (`source/tests/fixtures/rack_probe.carxp`) and asserts the layout invariants that regressed this week: no item wider than the rack viewport, square LED tiles opted out of button chrome, unpinned dials (size hint == minimum hint), fixed heights honored, and zero tracebacks in the app log. `claramsg rack detail` dumps per-slot LED/dial geometry.

#### 2026-11-11 — Rack item fixes (LEDs and knobs)

- **fix(ui)**: root cause of the clipped LED "traffic lights" was the global theme QSS (`QPushButton { min-height: 22px; padding: 4px 12px; }`) inflating every `LEDButton` to 14x32 inside a 30px grid. LED tiles now opt out of button chrome via a `ledTile` property exemption in the theme QSS, so they are exactly their hint size.
- **fix(ui)**: rack items overflowed to the right of the rack list — the title `QLabel`'s minimum width (full un-elided text) pushed each slot's minimum above the list viewport, so embedded widgets stuck at ~368px in a ~276px column. The title now uses an `Ignored` horizontal size policy (it already elides), and `RackListWidget` re-fits embedded item widgets to the viewport width on resize and after creation. Added `claramsg rack` to inspect rack list geometry.
- **refactor(ui)**: the modernized slice is now hint-driven instead of pixel-pinned — no `setFixedSize` on the LED grid container, tiles or meters; `LEDButton` declares its own natural size (`MINIMAL_LED_SIZE` hint) in minimal mode, and the vertical meters honor their `minimumSizeHint` with free vertical stretch.

- **fix(ui)**: rack knob rendering was broken — the raw SVG child widget painted itself over the custom-drawn knob (dark ghost + misplaced arc), knobs were forced to 68x54/52x48 while painting and layout hints stayed at 34px (overlapping knobs), and the value line under the label was clipped. The SVG child is now hidden (paint code renders it), forced dial sizes removed so layout matches painting, and dial height leaves room for the label + value lines.
- **fix(ui)**: modernized-slice LED "traffic lights" didn't fit their container — the 2x2 LED grid grew from 8px tiles in an 18x18 box to 14px tiles in a 30x30 box (matching the LED icon size), and the vertical meters now match the slice height. Verified in expanded and compact slots.

#### 2026-11-11 — Selected-node cable styling

- **feat(canvas)**: cables attached to a selected node can switch to their own routing (linear, bezier, stepped, ...), stroke pattern and thickness, then restore when deselected. Configured under Settings > Patchbay > Cables: enable, selected routing, selected pattern, selected thickness, and "skip when all nodes are selected" so selecting the whole graph stays visually quiet.
- **feat(msg)**: `claramsg canvas select <node ids|all|none>` selects nodes by graph id, which made this testable end to end.

## [1.2.0] - 2026-11-11

Clara 1.2.0 makes theming consistent end to end (rack, patchbay, dialogs) and fast, gives the patchbay usable node shadows, repairs nested Carla-Patchbay projects so they load, save and round-trip, and adds a scriptable control channel plus a UI smoke test. It also fixes autosave creation, the extra nested tray icons, and restores bridged LV2 state generically.

### Changed

#### 2026-11-10 — Theme switch repaints the whole UI

- **perf(theme)**: a theme change repolishes only the top-level windows instead of `QApplication.setStyleSheet`, and the rack list stays attached. Chrome settles in ~0.55 s on the 25-plugin test project (was ~2.0 s) and the last slot repaints at ~1.9 s (was ~5.5 s).
- **perf(rack)**: rack slots restyle in place (`PluginSlot_Minimal.restyle()`) instead of being destroyed and rebuilt. No SVG reloads, no item-widget churn, and the UI keeps responding while the slots update.
- **fix(theme)**: light themes had `text-primary` mapped to the background color, so all text was invisible. The semantic map now always uses `base05` for text.
- **fix(theme)**: the save-status label and splitter hover use theme tokens/palette roles instead of `#ffaa00` and `#8aadf4`.
- **fix(rack)**: slot backgrounds come from the active palette, and a slot keeps the monochrome palette that matches its own dark/light skin, so text stays readable when the app theme and the slot skin differ.
- **fix(theme)**: theme switching no longer defers until a modal settings dialog closes; the palette, chrome, and rack update immediately.
- **test(theme)**: added a contrast check for `text-primary` versus `bg-primary` on every bundled theme.

#### 2026-11-10 — Widget code no longer hardcodes theme colors

- **refactor(theme)**: the plugin list, project-loading banner and dialog, update/support banners, About dialog, settings form and settings glyph icons now read their colors from the theme engine instead of Catppuccin literals, so they follow the active theme (including light themes).
- **fix(theme)**: the inline plugin rename box, scalable dials and slot backgrounds derive from the active skin palette.
- **test(theme)**: new lint rejects a color literal in widget code unless it sits next to a token lookup (fallback) or the file is on the explicit allowlist (named palettes, user-facing swatches, LED meters, the separate patchcanvas theme).

#### 2026-11-10 — Rack slots follow the app theme

- **fix(rack)**: rack slots no longer pin a dark skin. A slot keeps its layout variant (minimal / sliders) but takes dark or light from the active app theme, both on load and on a live theme switch, so a light theme no longer shows a dark rack. A slot explicitly set to the opposite mode keeps its choice.
- **fix(rack)**: every remaining fixed color in the slot paint and stylesheets (button hovers, bypass/power tints, disabled text, combo and spinbox backgrounds, slider hover, selection and shadow outlines, classic and calf slot chrome, category stripe fallback) now comes from the skin palette.
- **fix(rack)**: the Appearance > Color swatches and the inline rename box use the active palette too.
- **fix(canvas)**: the minimap's floating "Map" button uses theme tokens instead of fixed dark colors.

#### 2026-11-10 — Rack inherits the theme background

- **fix(rack)**: the rack list is transparent again, so the theme background shows through instead of a `palette(base)` panel one step lighter than the window. The existing transparent rule targeted the plugin-list dialog's object name, so the rack never matched it; `rackListWidget` is now covered too.
- **refactor(rack)**: dropped the `QOpenGLWidget` viewport swap, which bypassed style painting, and the empty `paintEvent` override. The rack keeps drag-to-reorder, selection, smooth scrolling and the floating Add Plugin button.

#### 2026-11-10 — Patchbay follows the theme and updates live

- **fix(patchbay)**: theme changes never reached the canvas. `canvas.clear()` (run on every patchbay refresh) set `initiated = False`, so every live-update guard bailed out for the rest of the session. `clear()` now only drops items.
- **fix(patchbay)**: a theme switch now re-reads every canvas item, including the cached port pens and the cached cable pulse colours, through a single `patchcanvas.updateTheme()`.
- **refactor(patchbay)**: all canvas colours come from the resolved theme: node fill/header/text/outline, shadows, ports and cables, selection, rubberband, grid dots, drag ghosts, container chrome and node toolbar, role badges and the info panel. The canvas theme now only supplies structure (fonts, port mode, sizes) while the app theme supplies the colours.
- **fix(patchbay)**: node category badges were never shown because `CATEGORY_BADGES` did not exist in `carla_skin`; they now resolve from the category tokens.

#### 2026-11-10 — Clara Light replaces Catppuccin Latte

- **feat(theme)**: new **Clara Light** theme (neutral light palette, high-contrast text, blue accent) replaces Catppuccin Latte, which is removed from the registry, the canvas theme list and the bundled QSS files.
- **fix(theme)**: a saved theme that no longer exists (removed or renamed) now falls back to Catppuccin Macchiato instead of leaving the window unstyled. The settings dialog selects the same fallback.
- **refactor(theme)**: the application theme list is built from the registry, so every bundled theme (Nord, Tokyo Night, Dracula, Gruvbox) is selectable instead of a hardcoded list of four.
- **fix(patchbay)**: node shadows were painted with the canvas background colour, so they were invisible and every node looked flat. The shadow is now a translucent black (softer in light themes), with a small vertical offset and a wider blur, and layout containers get the same shadow.
- **fix(patchbay)**: the shadow blur/offset now follow the view zoom, so the shadow keeps the same visual weight instead of growing as you zoom out.
- **feat(msg)**: `claramsg shot [LOC]` saves a PNG of the window (patchbay included) or the active dialog; LOC may be a file or directory and defaults to the current directory. `claramsg screenshot --path` still works.
- **feat(settings)**: the patchbay settings get a shadow box: spread (blur), distance (offset), opacity, and a "keep shadows while dragging nodes" toggle. The existing "Node drop shadows" checkbox now actually controls shadows (it was stored but never read).
- **fix(canvas)**: applying settings no longer logs "PatchCanvas::init() - already initiated"; the canvas refreshes its theme and shadows instead.
- **fix(settings)**: the canvas settings were never copied into the live canvas options, so shadow spread/distance/opacity and the drag toggle appeared to do nothing. They now apply immediately.
- **feat(msg)**: `claramsg settings` drives the settings dialog: `open`, `pages`, `page <name>`, `fields [page] [-j]`, `get <id>`, `set <id> <value>`, `apply`, `close`, `reset --force`. `claramsg canvas zoom <scale|in|out|fit|reset>` and `canvas state [-j]` control and report the patchbay view, so visual changes can be scripted and verified with `claramsg shot`.

#### 2026-11-11 — Nested patchbay projects load again

- **fix(engine)**: nested Carla-Patchbay chunks were decoded twice. `CarlaStateSave` unescaped the `<Value>` text even though the XML parser had already done it, so a nested chunk containing another project lost one escaping level and failed to parse. Chunk values now keep exactly one decode, matching how they are written.
- **fix(engine)**: the chunk parser rejected the stored XML prolog/DOCTYPE, so `setState()` now starts at `<CARLA-PROJECT>`/`<CARLA-PRESET>`.
- **fix(engine)**: an empty state no longer wipes a plugin's plugins before parsing.
- Verified with upstream #1715's `layer 3` project: three nesting levels load with 3/2/1 plugins, save keeps the full structure, and reloading the saved file reproduces the same counts.

#### 2026-11-10 — Port labels follow the theme

- **fix(patchbay)**: port labels kept their old colour after a theme switch because ports are stored in `canvas.port_list`, not under the group, so `updateTheme()` never reached them and their cached pens stayed stale. Port widgets are now refreshed explicitly; `canvas state` also reports the resolved node/port theme colours for testing.
- **chore(engine)**: the failed-nested-load log now includes the engine's last error and the start of the state, which is what identified "Failed to parse project file".

#### 2026-11-10 — Nested project state is never destroyed on save

- **fix(engine)**: a nested Carla-Patchbay project that fails to load is now detected (the loader returned false and the child had zero plugins). Saving then returns the state that was originally loaded instead of serializing the empty child engine, so nested data is no longer wiped. Reproduced with upstream #1715's `layer 2/3` projects: the saved chunks keep every inner plugin.
- **fix(msg)**: `claramsg quit` waits for the process to exit, because its cleanup unlinks the socket, and a fast restart could delete the new instance's socket and lock.

#### 2026-11-10 — One tray icon only

- **fix(window)**: nested plugin windows and control instances no longer add their own system-tray item; the tray is reserved for the standalone app. `claramsg status` now reports `tray`, so scripts can verify it.

#### 2026-11-10 — Nested project loading and the autosave folder

- **fix(project)**: autosaves failed with "Failed to write file" whenever the `.autosaves/<project>` folder did not exist yet. The folder is now created before the backend writes the autosave; this is what popped up when opening a nested Carla-Patchbay UI.
- **fix(msg)**: `claramsg plugin ui <id> [off]` opens or closes a plugin's custom UI, which makes nested instances testable. A plugin host no longer inherits the parent's `CLARA_INSTANCE_KEY`, so several nested instances keep separate sockets.

#### 2026-11-10 — Instance discovery and UI smoke automation

- **feat(msg)**: `claramsg instances` lists running instances (pid, kind, project), `--instance <pid|key|latest>` targets one, `wait --ready|--dialog` replaces guessy sleeps, and `quit [--force]` closes the window through the normal path (refuses unsaved edits without `--force`).
- **feat(plugin)**: a nested Clara loaded as a plugin now starts its own control channel and registers itself, so `claramsg` can drive and screenshot plugin-host UIs too. Each plugin host gets a pid-scoped socket.
- **test(ui)**: `scripts/ui_smoke.py` launches a scratch instance under its own instance key, checks the shadow settings, canvas zoom, screenshot and theme switch, restores the settings it touched and quits.

#### 2026-11-10 — Clara Light is softer

- **style(theme)**: Clara Light no longer uses near-white backgrounds. The window/canvas is a soft grey (`#e9eaee`), cards and node bodies are off-white (`#f5f6f8`), text is Apple-style `#1d1d1f`, with quieter borders and a calmer blue accent. Layering now comes from surface tones plus the drop shadows instead of glare.

#### 2026-11-10 — One theme for the whole UI

- **refactor(settings)**: the separate "Canvas theme" selector is gone. The patchbay already takes every colour from the app theme; the profile now only supplies structure, so the picker was lying. The dead bundled `styles/themes/*.qss` files (unreachable since the engine compiles `base_primitives.qss`) are deleted too.
- **refactor(settings)**: the Patchbay page is regrouped into Nodes, Cables, Node shadows and Rendering.
- **feat(settings)**: shadow spread, distance, opacity and the drag toggle preview live on the canvas while the dialog is open, instead of waiting for Apply.
- **test(settings)**: a hookup test fails when a canvas key read by `setupCanvas()` is missing from `fSavedSettings` — the exact way the shadow sliders ended up doing nothing. It also caught the arrange style, which was never loaded.

### Style

#### 2026-11-05 — No boxes around the CLI banner and Ctrl+C prompt

- **style(cli)**: the startup banner and the terminal SIGINT prompt print their styled text directly instead of inside a rich `Panel`; the content and colors are unchanged.

### Changed

#### 2026-11-07 — Theme changes propagate without freezing

- **fix(theming)**: an applied stylesheet caches `palette(...)` colors, so a palette swap alone did not repaint themed widgets. The stylesheet is now reapplied after the settings dialog closes (the dialog itself previews with its own copy), so theme colors actually reach the whole UI.
- **perf(widgets)**: plugin edit dialogs are created lazily. Eager creation built 25 hidden `PluginEdit` windows (~11k widgets); the tree drops from ~18.8k to ~7.2k widgets and a full QSS reapply from ~5.5s to ~3.1s.
- **perf(theme)**: the reapply detaches the rack list first, cutting the chrome-only repolish to ~1.2s, then rack slots restyle at one slot per event-loop turn. Selecting a theme no longer blocks on the full 25-slot rebuild.
- **fix(svg)**: scalable dial/button SVG images are parented to their owner instead of becoming ~1k top-level widgets.

#### 2026-11-07 — Instant theme switching and themed rack surface

- **perf(theming)**: the global QSS now uses Qt palette roles instead of compiled color literals. A theme change swaps `QApplication` palette (~4 ms on a 25-plugin project) instead of calling `setStyle()` plus `setStyleSheet()`, which repolished every widget twice (~12 s total).
- **fix(rack)**: the rack list no longer paints its own background rectangle and inset outline, and the splitter handle no longer uses the Fusion default line. Both now follow the active theme/palette.
- **fix(theming)**: rack slots rebuild from the active tokens after a theme change, so per-slot colors no longer stay at their construction-time theme. The rebuild is one slot per event-loop turn and waits for the settings dialog to close, so selecting a theme no longer blocks the UI for the full rack restyle (~4s).
- **test(theme)**: `source/tests/test_theme.py` rejects color literals in `base_primitives.qss` and checks token-to-palette role mapping.

#### 2026-11-07 — Generic bridged LV2 state restore

- **refactor(bridge)**: custom-data messages are applied even while the plugin is disabled, and `state:restore` now runs once after the whole custom-data batch instead of being interleaved with it. This works for every bridged LV2 plugin, not just sfizz; the sfizz-specific `patch:Set` workaround was removed.
- **why**: non-bridged plugins fill the custom-data map and call `restoreLV2State()` in-process, so ordering is guaranteed. Bridged plugins send custom data and the restore request as separate shared-memory messages, so the bridge could see the restore first; the `isEnabled()` guard then dropped the data entirely during project load.
- **verified**: sfizz restores the Salamander instrument, and the bridged LSP Mixer x8 Stereo (4 instances) and LSP Autogain Stereo now receive their project custom data and run `state:restore` with the full key set.

#### 2026-11-07 — Bridged LV2 custom data and sfizz state restore

- **fix(bridge)**: bridged plugins now receive LV2 custom data even while the plugin is still disabled (the previous `isEnabled()` guard dropped it during project load).
- **fix(lv2)**: sfizz state path keys are applied as a `patch:Set` and also stored in the custom-data map, then the bridge re-runs `restoreLV2State` after receiving `sfizz:sfzfile`. Project loads now restore the saved instrument instead of falling back to `DefaultInstrument`.

#### 2026-11-07 — Hide expected duplicate-bundle warning

- **fix(logging)**: lilv's `lilv_world_add_plugin()` warning when a user-local bundle shadows the system bundle is DEBUG. It is expected when testing the patched sfizz, not a load failure.

#### 2026-11-07 — sfizz path investigation; samples tree no longer needed

- **fix(sfizz)**: upstream sfizz already canonicalizes the SFZ path (PR #303) and normalizes Windows separators, so the Salamander `48khz24bit` sample-tree symlink is unnecessary. The compat shim now recreates only the mapped SFZ/tuning links; verified with `/tmp/sfizz` containing no sample tree and sfizz loading with 0 errors.
- **fix(logging)**: the `[sfizz] Loading failed` line is the LV2 wrapper intentionally clearing the previous instrument before restore; it is DEBUG now, so real parse/state errors stay visible.
- **docs(todo)**: record the remaining symlink dependency as Carla-side mapPath/upstream sfizz-ui #16, not an sfizz loader bug.

#### 2026-11-07 — sfizz compatibility shim

- **fix(sfizz)**: before loading a project, recreate the temp layout the saved sfizz state expects (`/tmp/sfizz/sfizz` links for the user/SFZ tuning files, plus the Salamander `48khz24bit` sample tree). Clearing `/tmp` no longer makes every sfizz instance fail its path restore. Adds `test_sfizz_compat.py`.
- **TODO(FIX)**: theming is slow and the rack background is hardcoded in `patchbay_view.py`; tracked in `TODO.md`.

#### 2026-11-07 — Clean terminal prompt and repeated assertions

- **fix(ui)**: the Ctrl+C quit prompt now writes to the saved terminal fd, not captured stdout, so it no longer appears as `INFO ENTER`/`INFO T` log lines.
- **fix(logging)**: sfizz `Mapping abstractPath`, region/master counts, `File changed to`, `Will use LV2 X11 UI`, `audioMasterAutomate` and `Previously saved client` are DEBUG. `[carla]` is removed even when interleaved mid-line. Identical assertion failures are collapsed to one per 5 minutes with a suppressed count.

#### 2026-11-07 — Backend stdout joins the log

- **fix(logging)**: the GUI host now captures backend/bridge stdout (fd 1) as well as stderr, so raw `[carla]` lines are formatted and classified instead of leaking to the terminal. `Mapping absolutePath` and `Creating symlink` are DEBUG noise. The `CanvasBox.removePort(...) unable to find port` teardown message is DEBUG too.

#### 2026-11-07 — Restore plugin-browser Qt imports

- **fix(pluginlist)**: `QComboBox` was dropped when the PyQt conditionals moved to `qt_compat`, crashing the patchbay context menu's Replace action with `NameError`. Restored it and added the two `carla_backend_qtweb` names the static import check found missing.

#### 2026-11-07 — Shells wait for late clients

- **fix(patchbay)**: shell finalize no longer fires a fixed 1.2 s after load. It waits until client-added callbacks have been quiet for 2 s (up to ~20 s), so a reload whose clients arrive later still binds every skeleton. Verified: reload binds 25/25, drops 0.

#### 2026-11-07 — claramsg save

- **feat(cli)**: `claramsg save` saves the open project in place and reports the path. It clears the dirty flag, so automation can save before `open`/reload without a GUI prompt.

#### 2026-11-07 — Skeletons survive a reload

- **fix(patchbay)**: `bindGroupShell` retries with the base client name after stripping JACK's duplicate suffix (`-01`, `-02`, ...). Reloading with the engine running no longer leaves the new (suffixed) client unbound while the saved shells are dropped at finalize. Adds `test_shell_binding.py`.

#### 2026-11-07 — Track the canvas aggregator

- **fix(build)**: `canvas_ui.py` matched `.gitignore`'s `*_ui.py` and was never committed, so a clean checkout could not import the host. Renamed to `canvas_api.py` and added to the install lists.

#### 2026-11-07 — Loading banner takes over

- **fix(loading)**: when a recent-project/autosave prompt already owns `fLoadingDialog`, starting the actual load now closes it and shows the inline loading banner instead of silently reusing the prompt. Banner construction failures are logged instead of swallowed.

#### 2026-11-07 — Readable log lines

- **style(logging)**: console and file lines are now `HH:MM:SS  LEVEL     TAG        message` with aligned columns; DEBUG messages render dim. `claramsg events` uses the same columns. Connection/disconnect/stereo/scan messages use `→` and drop stale prefixes; the giant periodic `SIGNALFLOW` dump is opt-in via `CLARA_DEBUG_SIGNALFLOW=1`.
- **fix(logging)**: assertion failures are always ERROR again; the benign-expression filter used to demote `assertion failure: "size > 0"` to DEBUG. `engineCallback: PLUGIN_ADDED` and desktop-log chatter are DEBUG now.

#### 2026-11-07 — Quiet the INFO log

- **fix(logging)**: internal chatter no longer shows at INFO: patchbay mouse-release/connection requests, shell-size diffs, container/group AABB audits, canvas-position counts, viewport detection and plugin-discovery start/finish are DEBUG now. AABB audits still warn when something actually overflows, and their summaries warn only when mismatched. Removed the stale `carla_canvas:`/`[SCANNER]` prefixes.

#### 2026-11-06 — Clean log capture

- **fix(logger)**: ANSI codes are stripped before control characters, so the escaped `\x1b` byte can no longer leave literal `[31m`/`[0m` in history, the UI or `claramsg events`. Leftover (already-ESC-stripped) color codes are cleaned too, and red/yellow prefixes map to ERROR/WARNING when the message has no severity word. `LogEntry` sanitises every message, not just captured stderr.

#### 2026-11-06 — Single Qt compatibility layer

- **refactor(qt)**: removed the per-module PyQt5/PyQt6 import conditionals and import everything through `qt_compat` again: `plugin_edit.py`, `project_dialogs.py`, `carla_widgets.py`, `carla_app.py`, `carla_shared.py`, `carla_instance.py`, `osc_control.py`, `carla_backend_qt.py`, `carla_logger.py`, `dialogs/jackappdialog_py.py`, `utils/qsafesettings.py`, `pluginlist/pluginlistdialog_py.py` and `pluginlist/startup_scanner.py`. `qt_compat` now also exports `QByteArray`, `QCoreApplication`, `QDir`, `QLibraryInfo`, `QLocale`, `QTranslator`, `QT_VERSION_STR`, `PYQT_VERSION_STR`, `QListView`, `QRadioButton` and `QToolBox`. Generated `ui_*.py` and `resources_rc.py` are untouched.

#### 2026-11-06 — Driver settings split out

- **refactor(settings)**: `DriverSettingsW` and `RuntimeDriverSettingsW` moved to `driver_settings.py`; `carla_settings.py` keeps the main `CarlaSettingsW` and is 1,765 lines (from 2,103). The glyph icon cache is owned by the module that uses it. Engine menu imports updated.

#### 2026-11-06 — Widgets split: plugin editor and project dialogs

- **refactor(widgets)**: `carla_widgets.py` (2,151 lines) now re-exports `plugin_edit.py` (`PluginParameter`, `PluginEdit`) and `project_dialogs.py` (`ProjectLoadSummaryDialog`, `ProjectLoadingDialog`, `InlineLoadingBanner`), leaving a 134-line aggregator. Fixed a latent `_app` NameError in the plugin editor close path. Install lists updated.

#### 2026-11-06 — Canvas split into cohesive modules

- **refactor(canvas)**: `carla_canvas.py` (2,621 lines) split into `canvas_logic.py` (stereo patchbay helpers), `canvas_helpers.py` (event/glyph/lock helpers), `canvas_toolbar.py` (navigation palette), `canvas_context_toolbar.py` (context palette), `canvas_viewport.py` (viewport input/overlays) and `canvas_callbacks.py` (global patchbay callback). `canvas_api.py` re-exports the same names, so host/patchbay imports only changed module name. Install lists include the new files.

#### 2026-11-06 — App menus and host internals extracted

- **refactor(host)**: About/Disk/Transport menu actions moved to `app_menus.py`; logs, timers, misc helpers and internal utilities moved to `host_internal.py`. `host_app.py` is now 3,377 lines (under the 3,500 target). Also fixed a latent `haveLRDF`/`ladspa_rdf` NameError by importing the existing parser with a guard.

#### 2026-11-06 — Canvas input extracted

- **refactor(host)**: canvas scrollbar state and keyboard shortcuts moved to `canvas_input.py` (`CanvasInputMixin`). `host_app.py` is 4,073 lines. Added to both install lists.

#### 2026-11-06 — Engine menu actions extracted

- **refactor(host)**: engine start/stop/config moved to `engine_menu.py` (`EngineMenuMixin`). `host_app.py` is 4,192 lines. Added to both install lists.

#### 2026-11-06 — Plugin menu actions extracted

- **refactor(host)**: the add-plugin/favourite/plugin-actions menus and the startup plugin scanner moved to `plugins_menu.py` (`PluginsMenuMixin`). `host_app.py` is 4,346 lines. Added to both install lists.

#### 2026-11-06 — File menu and recent projects extracted

- **refactor(host)**: recent-project bookkeeping/startup restore and the File menu actions moved to `project_menu.py` (`ProjectMenuMixin`). `host_app.py` is 4,657 lines. Added to both install lists.

#### 2026-11-06 — Settings UI extracted from the host

- **refactor(host)**: the settings persistence, dialog launch and Settings/View menu actions moved out of `host_app.py` into `settings_panel.py` (`SettingsMixin`). `HostWindow` inherits it; `setEngineSettings` is imported lazily to avoid a cycle. `host_app.py` is now 4,936 lines. Added to both install lists.

#### 2026-11-06 — Host module and OSC control renamed

- **refactor(naming)**: `carla_host.py` → `host_app.py` and `carla_host_control.py` → `osc_control.py`. Updated the `carla`, `carla-control`, `carla-rack`, `carla-jack-*`, `carla-plugin`, `carla-patchbay` and `carla-rest-frontend` entry scripts, the lazy imports in settings/widgets/skin, tests and both install lists. The generated `ui_carla_host.py` keeps its name.

#### 2026-11-06 — Semantic, carla-free module names

- **refactor(naming)**: renamed the hand-written split modules to names that say what they do: `carla_host_events.py` → `window_events.py`, `carla_host_minicanvas.py` → `minimap.py`, `carla_host_canvas.py` → `patchbay_view.py`, `carla_control.py` → `local_control.py`, `carla_rewire_flow.py` → `rewire_flow.py`. Imports, tests and both install lists follow. Generated `ui_*.py` files are untouched.

#### 2026-11-06 — Host split: events, minimap, canvas

- **refactor(host)**: window events/timers/system tray/update checks (`carla_host_events.py`), MiniCanvas controls (`carla_host_minicanvas.py`) and the patchbay canvas setup/menu/callbacks (`carla_host_canvas.py`) moved out of `carla_host.py` into mixins that `HostWindow` inherits. No call sites changed; `carla_host.py` drops from 7,486 to 5,574 lines. Both install lists include the new files.

#### 2026-11-06 — Rewire flow extracted and tested

- **refactor(host)**: the control-channel handlers (`msgEvents`, `msgScreenshot`, `msgDialogs`, `msgDialogAction`, `handleMsgRequest`) and control-driven project open moved to `carla_control.py` (`ControlMixin`); the replace/rewire flow moved to `carla_rewire_flow.py` (`RewireFlowMixin`). `HostWindow` inherits both, so no call sites changed. `carla_host.py` is 700 lines shorter; both new files are added to the install lists.
- **test(rewire)**: new `test_rewire_flow.py` drives the offscreen host flow with fake canvas groups: adoption keeps position, color, hide state, split and container membership; the poll adopts as soon as the new client appears; finishing rewires the cables and sweeps the ghost.
- **fix(rewire)**: a leftover group for the replaced client (multi-client JACK can leave a zero-port client behind with no removal callback) is dropped after the rewire, with a 2 s follow-up sweep for late unregistration.

### Features

#### 2026-11-06 — Scraped LV2 port-role catalog

- **feat(rewire)**: ship an 85 KB role catalog for 531 installed LV2 plugins, generated from `lv2ls`/`lv2info` by `scripts/scrape_lv2_port_roles.py`. Roles come from port names, LV2 designations, port groups and position: `ch:N` (main), `sc:N` (sidechain), `event` (MIDI), `cv:N`.
- **feat(rewire)**: matching now goes exact name → canonical role → position. Sidechain ports never map to main inputs, repeated names (mixers, repeated L/R buses) fall back to position, and reversed L/R order matches correctly. The same catalog is applied to the old plugin and to the replacement when its label is known.
- **test(rewire)**: covers sidechain isolation, reversed channels, generic names with catalog roles, mixer role uniqueness and repeated names.

#### 2026-11-06 — claramsg automation

- **feat(cli)**: add the `claramsg` entry point (same client as `clara msg`) and automation commands: `events` (filterable log history), `screenshot` (window or active dialog PNG), `dialogs` and `dialog accept|cancel|click` (drive visible dialogs), and `replace <node> --with-plugin <node> [--apply|--dry-run]`.
- **feat(rewire)**: replace accepts an already-loaded plugin as the target, so automation skips the browser. `--apply` runs the matcher without the dialog and waits for the result; `--dry-run` reports the mapping only. The engine creates a new patchbay client on replace, so the old node's position, color, hide state and container membership are adopted and the empty old group is removed.
- **test(rewire)**: matcher tests cover name/channel/event matching, role resolution, direction/kind refusal and duplicate-output rejection.

#### 2026-11-06 — Replace plugin with rewire

- **feat(patchbay/rack)**: “Replace…” now opens a Rewire dialog instead of swapping the plugin blindly. It lists the old node's wired ports, auto-matches by name → channel/index → event/CV role, and lets each row be remapped or dropped before applying. Cables are preserved by direction: an old output reconnects to the same peer input, an old input keeps its peer output.
- **feat(rewire)**: when the replacement plugin is already loaded elsewhere, its live ports are used for an exact preview (no extra load). Otherwise the dialog shows roles (`Audio Out #1`, `Event In`) resolved after the plugin loads. Outputs cannot be double-mapped; unmatched cables are reported as dropped.
- **test(rewire)**: pure matcher tests cover name/channel/event matching, direction/kind refusal, role resolution and duplicate-output rejection.

#### 2026-11-06 — Per-plugin "never bridge" overrides

- **feat(bridge)**: `CanvasPositions` now stores `no_bridge_plugins`. On load those indices get `AVOID_BRIDGE` and lose `USE_BRIDGE` even if an older map still lists them; the learned map subtracts them on save. Used to unbridge the four LSP `mixer_x8` nodes (18 → 14 bridge processes). Total memory stayed roughly flat (~3.7 GB) because the plugin data moved in-process; the win is fewer processes, not less sample RAM.

#### 2026-11-06 — Single instance lock and control channel

- **feat(instance)**: replace the fixed-path raw socket with a per-session `QLockFile` lock plus a `QLocalServer` channel. The lock is taken before Qt starts and the channel listens before the host/GUI, so a second launch forwards `SHOW` or `OPEN <project>` to the running window instead of starting another. `--no-gui` / control processes do not take the GUI lock. Old fixed-path instances are detected once for migration.
- **feat(cli)**: `clara msg status|show|list nodes|connections|containers` (`-j` JSON, `--tree`, `--full`). It is Clara-only: `carla msg` is rejected with a pointer to `clara msg`. One `canvasSnapshot()` in the host feeds both this CLI and future UI dumps, so there is no second model.
- **test(instance)**: pure identity/protocol checks run in CI; a separate Qt job covers the lock race (8 concurrent processes, one winner), server/client framing and legacy `SHOW`.

#### 2026-11-06 — claramsg help and canvas polish

- **feat(cli)**: `claramsg --help`, `claramsg help` and `clara msg --help` print a comprehensive control-client help (overview, every command and flag, id rules, output/exit codes, notes) instead of the Carla host help, and it starts by pointing at `claramsg --examples`. `claramsg --examples` (or `claramsg examples`) prints grouped copy-paste examples. Help and examples are colourised headings, command names, flags and tool name on a TTY, plain when piped, and honour `NO_COLOR`. Running with no arguments prints help and exits 0.
- **fix(patchbay)**: the replacement client is adopted into the old node's position/container as soon as it appears, instead of after all ports arrive, removing the double-node/shrink jank. Stale client-removed callbacks are ignored.
- **fix(canvas)**: the floating navigation and context toolbars cannot be dragged while a project is loading.
- **fix(screenshot)**: screenshots now render the patchbay scene into the window grab, so the canvas is included next to the rack. Fixed Qt 6 `QImage.Format` and `QRectF` usage for the composite.

### Fixed

#### 2026-11-06 — CLI errors, dirty status and safe dev restarts

- **fix(cli)**: `claramsg` argument errors are no longer swallowed by Carla's stderr capture. Bad usage (for example `claramsg list -j` without a target) now prints the usage and error and exits 2; unknown commands do the same.
- **fix(cli)**: `claramsg examples` no longer needs a running instance, like `--examples`.
- **feat(cli)**: `claramsg status` reports whether the project has unsaved changes (`dirty yes/no`).
- **fix(scripts)**: `scripts/run_clara_dev.sh` refuses to kill a running instance with unsaved changes (set `CLARA_DEV_FORCE=1` to discard them), uses SIGTERM before SIGKILL, and drops the obsolete fixed-socket cleanup.

#### 2026-11-06 — Audit fixes (data loss, rewire safety, control channel)

- **fix(session)**: opening a project through the control channel now refuses (CLI) or prompts Save/Discard/Cancel (GUI) when there are unsaved edits. If the new load fails, the previous project is loaded again instead of leaving an empty session.
- **fix(bridge)**: `no_bridge_plugins` is stored as stable plugin names (legacy indices still load) and indices are remapped when a plugin is removed, so the setting follows the plugin instead of the slot.
- **fix(rewire)**: replacement honors the custom-UI bridge policy, refuses a target with no audio/MIDI/CV ports, waits up to 60 s for slow plugin ports instead of cutting at 3 s, and adopts split nodes. On a failed add the engine keeps the old plugin; that is now checked and logged.
- **fix(cli)**: `--with-plugin` is a plugin id and the new `--with-node` takes a node id; `claramsg open` is available; dirty opens fail with a clear message; the result wait is 75 s; `dialog click` refuses destructive button text without `--force`.
- **fix(security)**: the default screenshot is a private 0600 temp file and explicit paths refuse symlinks/special files.
- **fix(canvas)**: the delayed shell finalize is tied to a load generation, so a previous load can no longer drop a newer load's shells.
- **fix(tools)**: the LV2 scraper refuses a >20% catalog shrink without `--force`, catalog load errors are logged, and the AppImage gets a `claramsg` launcher. Catalog roles now match by port name when it is unique, with position as fallback.
- **feat(ui)**: the inline loading banner shows a READ-ONLY indicator while the project loads; the rack is disabled and the patchbay stays pannable but not editable until loading finishes.
- **fix(rewire/ui)**: the Rewire dialog title shows the plugin display name instead of the LV2 URI, and the table opens at the top instead of scrolled to the last port.

#### 2026-11-06 — Bridges must die with the host

- **fix(bridge)**: both bridge binaries set `PR_SET_PDEATHSIG` (Linux), exit if already reparented, and run a 1-second parent watchdog as a portable fallback. Without this, killing or crashing Clara left `carla-bridge-native` processes alive forever; a sample player held 2.5 GB of swapped memory after the host was gone. Verified: `kill -9` on the host now drops all 18 bridges within one second. The dev launcher also kills bridges by command line (`pkill -x` never matched the truncated 15-char process name). Orphaned bridges from earlier runs were cleaned up manually.

### Fixed

#### 2026-11-06 — Seamless patchbay load

- **fix(patchbay)**: the loading shell now matches the final node exactly. Shells are built before the engine enumerates clients (no duplicate nodes), existing clients are adopted in place, saved hide-unconnected state and port types are applied from the first frame, and the saved node size covers inline displays. `SHELLDIFF` reports 0 size differences on the test project.
- **fix(patchbay)**: ports and cables that arrive before their client are replayed on bind, and unclaimed shells/cables are only dropped 1.2 s after load, so pre-wired plugin connections bind instead of being discarded (72/72 cables bound).
- **fix(ui)**: the "load plugins bridged?" prompt is skipped when the project already stores a per-plugin `bridge_plugins` map.

#### 2026-11-06 — Group/container AABB audit

- **diag(patchbay)**: after a project load, log the AABB of every group's box against the AABB of all items drawn inside it (`GROUPAABB`), and every container's frame against the AABB of its complete member set (`CONTAINERAABB`). On the test project both report 0 overflow: content equals the boxes and stays inside the container frames.

#### 2026-11-06 — Containers hug their nodes

- **fix(patchbay)**: container frames no longer reserve a fixed 220 px minimum width. The minimum is now the header (controls + title), so narrow groups like *Buses* shrink to their member width and get the same 14 px gap on both sides. Empty containers keep the old minimum, and collapsed ports track the real frame edge.

#### 2026-11-06 — Container resize and member arrangement

- **fix(patchbay)**: containers can no longer be resized smaller than their members (the drag clamps to the member hull plus padding).
- **fix(patchbay)**: VBox and HBox containers are auto-sized, so their resize handles and cursors are disabled; Grid and Freeform stay resizable.
- **fix(patchbay)**: "Auto-Arrange Members" now reorders members by signal-flow layer in every layout mode (VBox/HBox/Grid re-apply their layout in flow order; Freeform lays them out in a row). Previously it silently did nothing outside Freeform.

#### 2026-11-06 — Remove unbound placeholder ports

- **fix(patchbay)**: after a load, any placeholder port the engine never replaced is now removed as a scene item, not only as a dict entry. Clicking one used to send a negative port id, tripping `CarlaEngineJack.cpp` ("fullPortNameA != nullptr") and reporting "Invalid or unsupported plugin type". Connecting to an unbound port is also refused client-side instead of reaching the engine.

#### 2026-11-06 — Hardened shell finalization

- **fix(patchbay)**: shell finalization is now exception-safe per group and always runs the placeholder-port sweep, so one deleted item can no longer skip the cleanup and leave clickable ghost ports. The refusal log names both ports so a lingering placeholder is identifiable.

#### 2026-11-06 — Bind shell port ids on the widget

- **fix(patchbay)**: binding a shell port updated the port dictionary but not the `CanvasPort` widget's own id. The connection code reads the widget id, so remapped ports kept sending their negative placeholder ids and were refused by the engine guard. The widget id/name now update with the dictionary, and the connection path uses the dictionary id as the source of truth. A post-load check reports any port whose widget id is still stale (currently 0).

### Features

#### 2026-11-06 — Per-plugin bridging

- **feat(engine/ui)**: plugins are now bridged individually instead of all-or-nothing. The project stores a `bridge_plugins` index list (learned from `PLUGIN_HAS_CUSTOM_UI` after a load); on load only those plugins get `PLUGIN_OPTION_USE_BRIDGE`, the rest load in-process. Inline-only plugins (JSFX meters, SF2/SFZ) stay native. First load keeps the old all-bridged behaviour, then a save records the map.

### Performance

#### 2026-11-05 — Signal-flow cost

- **perf(canvas)**: the animator runs at 30 FPS, level polling is cached for 100 ms, and only nodes/cables above the visible 0.05 level are repainted. Measured host CPU with signal flow: ~54% before, ~18% after (flow off ~15%).


### Fixes

#### 2026-11-04 — Session safety, updater hardening and cleanup

- **fix(session)**: a failed save is no longer reported as success
  - `saveProjectNow()` now checks the finalize step and shows the "Failed to save project" dialog instead of clearing the dirty flag and pruning autosaves for a file that was never written.
  - `ProjectStorageManager.finalize_from_backend_save()` returns `False` on any failure instead of always returning `True`; autosave finalization honours it too.
- **fix(session)**: a failed project load keeps the current session intact
  - `loadProjectNow()` returns `False` and stops before restoring canvas positions or clearing `fHasUnsavedChanges`, so closing still prompts and the previous work is not treated as saved.
  - Opening a corrupt file no longer leaves the unreadable filename attached to an empty rack.
- **fix(storage)**: project files are written atomically
  - XML canvas positions and XML save-as copies go through a sibling `.tmp` file + `os.replace()`, matching the JSON path; a crash mid-save can no longer truncate a `.carxp`.
- **fix(storage)**: loading a JSON project works from a read-only folder
  - Backend conversion files are created in the system temp dir via `tempfile.mkstemp()` instead of next to the project, and no longer litter the project folder.
- **fix(autosave)**: manual save only removes this session's autosave, not the whole `.autosaves/<project>/` folder, so a second running instance keeps its recovery copy.
- **fix(updater)**: the version string from `releases.json` is validated before being placed in the shell command, and `clara_self_updater.sh` rejects non-numeric versions (command-injection hardening).
- **fix(updater)**: update-check `QThread`s are deleted when finished and awaited on close, avoiding "QThread: Destroyed while thread is still running".
- **fix(widgets)**: "Copy Log to Clipboard" in the project-load error dialog no longer raises `NameError: QTimer`.
- **perf(canvas)**: signal-flow level polling is cached for 50 ms and skipped entirely while the canvas is hidden or the window minimized, cutting idle CPU for the 60 Hz animator.
- **chore(qt)**: `QDialogButtonBox.Apply` is now part of the `qt_compat` shim, replacing the per-call `getattr` workaround in the settings dialog.
- **feat(project)**: the engine writes and reads JSON projects directly
  - Added `source/includes/CarlaJsonDocument.hpp`: converts between the engine's project tree and `.carjp` JSON, covering attributes, repeated tags, empty elements, UTF-8 and `\u` escapes.
  - `CarlaEngine::saveProject()`/`loadProject()` choose by extension, so `.carjp` is serialized by the engine itself — no temp XML, no Python conversion, and no XML on disk for JSON projects.
  - New saves default to `.carjp`; `.carxp` stays readable and writable for backwards compatibility.
  - `project_storage.py` lost the XML↔JSON conversion (`xml_elem_to_dict`, `save_full_project_from_xml_path`); only the force-bridged pre-check writes a patched temp copy.
- **chore(launcher)**: `CARLA_SINGLE_INSTANCE_SOCKET` overrides the single-instance socket path, so a source build can run next to an installed Carla without activating it.
- **chore(cleanup)**: removed dead `tab_titles`/`tab_glyphs`/`nerd_family` block in the settings dialog, unused `old_line_*` locals in `patchcanvas.setOptions`, and an unused `error_entries` list in the project loader.
- **test(project_storage)**: added `source/tests/test_project_storage.py` covering XML/JSON round-trips, atomic saves, temp-file location and failure reporting.

### Fixes

#### 2026-11-04 — Signal-flow accuracy and cleanup

- **fix(patchbay)**: cable pulses now follow the source signal only
  - `signalflow.state` gained a `flow` map (source-side output level) separate from `levels` (node activity). A loud destination no longer makes an idle cable pulse, and external groups only flow from their own peak-detect tap, never borrowed from the far end.
  - Flow is peak-hold smoothed (0.4 attack / 0.82 decay) so brief dips do not make the pulse flicker.
- **chore(ci)**: added `.github/workflows/tests.yml` running the Python project-storage test and the C++ JSON document round-trip on push and pull request.
- **chore(cleanup)**: 27 bare `except:` became `except Exception:`; removed unused locals (`stylesDir`, `group_id`, `w`, `bypass_active`, `node_set`, `byp_w`, `btn_border`, `has_bypass_support`, `theme`, `pos1/pos2`, `ok`); `ExternalUI` no longer returns from a `finally` (it was swallowing pipe errors); dropped the dead temp-file branch in `saveProjectNow`.

### Fixes

#### 2026-11-04 — Shutdown, signal-flow and playback-node meters

- **fix(app)**: SIGTERM now always quits
  - `closeEvent` no longer touches a deleted `UpdateCheckThread` (`RuntimeError` aborted the close and left the app unkillable); the thread reference is cleared when it finishes.
  - Engine-stop retries run every 50 ms instead of a `singleShot(0)` busy loop that burned a full CPU core while waiting.
  - SIGTERM arms a 4 s watchdog (`os._exit`) so a stuck plugin bridge cannot hold a logout hostage.
- **feat(patchbay)**: signal flow for playback nodes (Spotify, browsers, Electron apps)
  - New `pwrecord` sampler captures a node directly with `pw-record --target`, since playback streams have no PulseAudio source. Used only for nodes the PulseAudio peak-detect sampler cannot resolve.
- **fix(patchbay)**: flow levels are copied to a client's split visual sub-groups (negative group ids). Cables attach to those boxes, so keying flow by the client id alone left every external cable dark while its node still glowed.
- **fix(patchbay)**: `pw-record` only starts for names that resolve to a node id. Unresolved names (e.g. `OUT-Laptop`, `Linux_Soundboard_Output`, which are Carla clients, not PipeWire nodes) are skipped instead of falling back to the microphone.
- **fix(patchbay)**: `pw-record` targets are resolved to PipeWire node ids via `pw-dump`. Targeting a sink by name made pw-record fall back to the default source (the microphone), so idle buses like BUS-SOUNDBOARD/BUS-YOUTUBE pulsed with room audio.
- **fix(patchbay)**: `pw-record` captures at 1 kHz instead of 50 Hz. Low capture rates resample some streams to near-silent peaks (Spotify read 0.003 at 50 Hz and 0.15 at 1 kHz), so those cables never crossed the pulse threshold.
- **fix(patchbay)**: `pw-record` was writing an AU container (`.snd` header), and the sampler read those bytes as float32, so every sampled node returned a garbage peak clamped to 1.0 — buses with no signal pulsed constantly. Added `--container raw`, so levels are real (idle buses now read ~0.01, below the pulse threshold).
- **fix(patchbay)**: the `pw-record` sampler strips the engine's `Client/Node` prefix (`Spotify/spotify` → `spotify`), so playback nodes actually bind and produce a level.
- **fix(patchbay)**: a reused client id no longer inherits the previous client's filtered state. The engine reuses ids without always sending a removal (e.g. a `pw-record` capture client disappears and its id is given to a plugin), so a real node could inherit a filtered id and lose all its ports. The filtered state is now recomputed on every client add, and cleared on a full canvas refresh.
- **fix(patchbay)**: ports that arrive before their client group are queued and replayed when the group appears (the engine does not guarantee callback order, which left some nodes without ports during startup/refresh); entries are dropped when the client is removed.
- **fix(patchbay)**: `pw-record` capture clients are hidden from the patchbay and never sampled themselves; sampling is capped at 8 nodes and disabled while a project loads. A self-sampling loop had stalled loading and churned the canvas.
- **fix(patchbay)**: the earlier "containers missing" state was an interrupted project load, not data loss; a clean load restores all containers (verified: 7 containers, 14 boxes).

### Fixes

#### 2026-11-04 — Honest load progress, quieter load

- **feat(ui)**: the project-load dialog now shows real progress instead of crawling to 93% and stalling
  - Plugin count is read from the project file, so the bar tracks `Loading plugin N/total` from 8% to 90%.
  - Canvas restore reports its own phases (93 positions, 96 containers, 97 layout, 99 finishing); 100% now appears only when the dialog closes.
  - The automatic crawl only runs while the real total is unknown.
- **perf(canvas)**: signal-flow animation is paused while a project loads, removing the 90–120% main-thread spike during load.

### Fixes

#### 2026-11-04 — Load in place: containers and positions first, rack paints while it fills

- **feat(ui)**: the canvas is prepared before the engine loads plugins
  - Saved group positions are seeded into `canvas.old_group_pos`, so each box is created at its final spot instead of jumping after the load.
  - Patchbay containers are created first; boxes join them as they appear via the existing standby-descriptor matching.
- **feat(ui)**: the rack keeps painting during load and scrolls to the top at the end, so rows appear in place instead of all at once (and offscreen).

### Fixes

#### 2026-11-04 — Autosave atomicity, quiet patchbay assertions, sampler tests

- **fix(session)**: autosaves are written to a sibling `.part` file and renamed into place, so a crash mid-write cannot leave a truncated autosave.
- **fix(engine)**: `CarlaEngineJack` no longer asserts `groupId != 0` for transient clients (capture/observer streams); it returns silently, removing the load-time assertion noise.
- **test(pwrecord)**: added `source/tests/test_pwrecord.py` (target naming, node-id resolution, never spawning with a name, ignoring our own capture clients) and wired it into CI.

### Fixes

#### 2026-11-04 — Containers update in place

- **fix(patchbay)**: `loadContainers()` updates existing containers by id instead of clearing and rebuilding them. It runs before load, after load and on the deferred sweep, so containers were recreated 3× (21 creations for 7 containers) and flickered.

### Fixes

#### 2026-11-05 — Ghost swap hides the node build

- **fix(ui)**: the real box is now created hidden while its ports arrive, and is revealed in the same tick the ghost is removed. Previously the ghost was deleted first, so the node was seen growing from a header-only box to its full size (the "re-render" after loading). A 1.5 s timeout reveals it anyway if the port count never matches.



#### 2026-11-05 — Load skeleton (ghost nodes)

- **feat(ui)**: at load start, every node in the project is drawn as a ghost box (name, saved position, port stubs from the recorded `left`/`right` lists). Each ghost is removed as its real client callback arrives; leftovers are cleared when the load finishes. This makes the whole patchbay visible immediately instead of filling in over ~11 seconds.



#### 2026-11-05 — Port names recorded in canvas positions

- **feat(project)**: `saveGroupPositions()` now stores each group's port names per side (`left` for the output box, `right` for the split input box) in `CanvasPositions`, in both `.carjp` and `.carxp`. This is the data a load-time skeleton needs to draw ports before the plugins exist.



#### 2026-11-04 — Load camera follows new nodes

- **feat(ui)**: while a project loads, the canvas centers on each node as its client callback arrives, so the view follows the patchbay being built instead of staying wherever it was.


- **feat(patchbay)**: spammable container header nerd font icons and targeted inline rename collision
  - Positioned container control buttons (`󰅖` ungroup, `󰘖`/`󰪦` collapse/expand, `󰝘`/`󰝙`/`󰝚`/`󰝜` layout switchers) at fixed coordinates on the left of the header for position stability.
  - Restricted double-click inline rename collision strictly to the title text boundary with minimum 5-character width, leaving the remaining header draggable.
  - Preserved original canvas layout and positions when grouping selected nodes into Freeform containers.
- **fix(patchbay)**: automatic lifecycle for all drawn canvas items across settings updates and refreshes
  - Made `setOptions()` live and non-destructive: theme, line style, stroke thickness, cable opacity, and node geometry update existing items in-place without clearing the canvas.
  - Added live scene and viewport invalidation to `CanvasLine` (`setShape`, `setStroke`, `setOpacityVal`, `updateLinePos`) with `prepareGeometryChange()` so existing lines immediately re-route visually when settings change.
  - Added `Apply` button to settings dialog and forced lazy schema form builders to initialize before save to persist all configuration tabs.
  - Removed destructive `patchcanvas.clear()` from `slot_configureCarla()`, preventing grouping boxes and layouts from disappearing when changing canvas settings.
  - Preserved `CanvasContainer` objects and custom node colors across canvas refreshes/clears using standby descriptors and color caching.
  - Re-link container standby descriptors in `setGroupAsPlugin()` when plugin IDs become available after group creation, preventing active rack plugins from reporting as unplugged.

- **fix(patchbay)**: prevent canvasbox sub-bar occlusion and resolve missing ports on asynchronous loads
  - Added dedicated shaded background strip and bottom separator for node sub-bars so buttons never clash with port rows.
  - Linked `_port_dict` directly to child `CanvasPort` items in `addPortFromGroup` and checked `childItems()` during `updatePositions` to prevent nodes from collapsing before global port lists settle.
- **fix(patchbay)**: forward all keyboard inputs to active scene focus items during inline rename
  - Fixed `DraggableGraphicsView` and `PatchCanvasScene` intercepting characters (`V`, `H`, `Q`, `Space`, `Escape`, `Ctrl+A/D/F/S`) while inline editing text items in the canvas.
- **fix(host)**: detect yabridge and Wine plugins in project bridge safety pre-check
  - Included `"yabridge"` and `"wine"` tokens and checked plugin `Binary` path during project loading to ensure Windows bridged plugins run sandboxed in separate processes rather than crashing the host in-process.
- **fix(patchbay)**: initialize external patchbay state on startup and sync menu actions
  - Initialize `fExternalPatchbay` from `Canvas/ShowExternal` settings on startup so PipeWire, PulseAudio, and ALSA nodes appear immediately without waiting for manual toggle.
  - Added container host execution fallback (`distrobox-host-exec`, `flatpak-spawn`) and backoff handling for `pw-dump` port name queries.
- **fix(engine)**: prevent `curPluginCount != 0` assertion failure on empty racks
  - Guarded `setGroupAsPlugin`, `carla_get_custom_data_value`, and `CarlaEngine::getPlugin` against querying `MAIN_CARLA_PLUGIN_ID` (0xFFFF) or out-of-bound plugin IDs.
- **fix(updater)**: resolve actual RPM release assets and use fail-safe curl
  - Query GitHub release assets dynamically in `clara_self_updater.sh` and use `curl -f` to avoid downloading 404 HTML error pages as invalid RPM packages.
- **fix(app)**: set desktop file name to `clara` for host portal registration
  - Set `desktopFileName` to `clara` (or Flatpak ID) to eliminate D-Bus host portal registration errors.
- **fix(packaging)**: disable detached debug package generation across all PKGBUILDs
  - Added `options=('!debug')` to root `PKGBUILD`, `PKGBUILD.local`, `aur/clara-git/PKGBUILD`, and CI template `.github/aur/PKGBUILD.in` to prevent spawning redundant `-debug` tarballs.


## [1.1.7] - 2026-10-29

Patchbay layout containers (VBox, HBox, Grid, Freeform), collapse cable rerouting to header slots, interactive resizing, transparent inline rename, and contextual toolbar integration.

### Fixes

#### 2026-11-05 — No fade on the ghost swap

- **fix(ui)**: a ghost-hidden box no longer unhides (with the eye-candy fade) when its first port arrives; it stays hidden until the swap. On reveal, any running fade animation for the box and its ports is stopped and opacity forced to 1, so the ghost is replaced in a single frame.


- **feat(patchbay)**: route collapsed container cables to header, enable inline rename and group resizing
  - Re-anchored cables of child nodes inside collapsed containers to the header edges so connections remain visible and neatly routed to the group.
  - Added interactive header drag movement, clickable header buttons (`[-]`/`[+]`, `[✕]`, layout switcher), and corner/edge resize handles with dynamic cursors.
  - Added inline rename editor on the container header via double-click or the Rename action.
  - Added `CanvasContainerType` to `DraggableGraphicsView` interactive items to prevent backdrop panning when clicking containers.
- **feat(patchbay)**: integrate container controls into floating contextual toolbar and batch actions
  - Display dedicated container controls (`[GROUP]`, rename, layout mode switcher, color swatch picker, collapse/expand, ungroup) when selecting a container.
  - Added "Group Selected Nodes into Container..." button (`icon_rack`) with layout mode popover on the batch action toolbar.
- **feat(patchbay)**: implement matching Catppuccin swatch bar color context menu for containers
  - Replaced text-only color list with the interactive Catppuccin horizontal palette bar, quick reset button, and native color dialog matching `CanvasBox`.

### Bug Fixes & Stability
- **fix(qt_compat)**: add Qt6 aliases for CursorShape and TextInteractionFlag
  - Exposed `Qt.SizeFDiagCursor`, `Qt.SizeHorCursor`, `Qt.SizeVerCursor`, `Qt.TextEditorInteraction`, etc. on `Qt` namespace for PyQt6 cross-compatibility.
- **fix(patchbay)**: prevent SIGSEGV during container inline rename with transparent QGraphicsTextItem
  - Replaced `QGraphicsProxyWidget` embedded `QLineEdit` with native `QGraphicsTextItem` to eliminate Qt6 proxy destruction crash.
  - Made inline rename background seamlessly transparent with `#cad3f5` foreground matching canvas header text.
- **fix(patchbay)**: fix AttributeError on container ungroup in contextual toolbar
  - Added `dissolve()` alias to `CanvasContainer` and invoked `ungroup()` with selection refresh from the contextual toolbar overlay.
- **fix(patchbay)**: allow container right-click context menu by including CanvasContainerType in scene event filter
  - Included `CanvasContainerType` in `PatchScene.contextMenuEvent` filter so right-clicking containers opens the container menu instead of canvas background actions.
- **fix(patchbay)**: fix NameError for `QColor` when restoring containers on startup
  - Imported `QColor` from `qt_compat` inside `loadContainers()` so container restoration succeeds without failing silently in `loadCanvasGroupPositionsFromProject`.
- **fix(storage)**: enable layout container metadata persistence and restoration
  - Subclassed `CanvasPositionList` so list objects can retain attached metadata attributes (`patchbay_containers`, `split_view_enabled`, `infinite_canvas`).
  - Added XML `<Containers>` element and JSON `Containers` support inside `<CanvasPositions>` to ensure container group definitions survive save and load cycles.
- **fix(host)**: auto-bridge DecentSampler to prevent in-process malloc crash on startup
  - Added `decentsampler` to risky plugin collision tokens and auto-sandbox bridging checks in `carla_host.py`.

## [1.1.6] - 2026-10-28

Patchbay performance overhaul: QOpenGLWidget hardware acceleration, item caching, 60fps animations, fast wire previews, and context-aware plugin placement.

### 2026-10-28 15:15:00
- **feat(patchbay)**: layout containers (VBox, HBox, Grid) with interactive drop zones and standby recovery
  - Added non-destructive backdrop layout containers (`CanvasContainer`) placed behind patchbay nodes (`z = -10`) without reparenting cables or altering port coordinates.
  - Eliminated movement drift and de-centering by anchoring child coordinates strictly to the container origin and bypassing canvas grid snapping for contained items.
  - Added dedicated right-click context menu to containers with **Rename**, **Catppuccin color accents**, **Layout mode**, **Collapse/Expand**, and **Ungroup**.
  - Supported double-clicking the container header to rename inline.
  - Interactive drag-and-drop ergonomics: dynamic slot gap preview lines, automatic child translation when dragging the container, and drag-out extraction.
  - Supported **VBox** (vertical stack), **HBox** (horizontal chain), **Grid** (matrix), and **Freeform** (unconstrained positions within an auto-fitting boundary frame) with header badge mode switching and ungroup button.
  - Synchronized cable visibility during collapse/expand so cables hide neatly when containers are minimized and reappear when expanded.
  - Added user confirmation prompt when clicking ungroup/remove, and kept child nodes at their exact canvas coordinates without stacking.
  - Persistent JSON project storage under `extra_metadata["patchbay_containers"]`.

### 2026-10-28 10:00:00
- **feat(patchbay)**: place added plugins at right-click location or viewport center
  - Forwarded right-click scene coordinates through context menu and canvas actions to anchor newly loaded plugins directly under the user's cursor.
  - Automatically center new plugins in the visible patchbay viewport when added from the sidebar, rack, or menubar.
  - Optimized moving wire drag preview by unparenting from cached ports into top-level scene coordinates with `NoCache` for stutter-free wire rendering.

- **perf(patchbay)**: migrate to QOpenGLWidget, smart viewport updates, and item caching
  - Migrated Qt OpenGL canvas viewport initialization from deprecated `QGLWidget` to `QOpenGLWidget` via `qt_compat.py` with safe runtime fallback.
  - Set `CARLA_DEFAULT_CANVAS_USE_OPENGL = True` and added a one-time migration (`Canvas/OpenGLMigrationV1`) in `source/frontend/carla_host.py` to enable OpenGL acceleration for existing user configs.
  - Applied `DontAdjustForAntialiasing` and `DontSavePainterState` optimization flags alongside `SmartViewportUpdate` to eliminate full canvas redraws.
  - Enabled `DeviceCoordinateCache` on `CanvasBox`, `CanvasPort`, and `CanvasIcon` items to eliminate redundant repainting of static node bodies, badges, and SVGs.
  - Bumped signal flow animation frequency to 60 FPS (16ms interval) for fluid visual pulses.
  - Implemented zero-allocation straight-line wire drag previews with sub-pixel deadband pruning and fast bounding-rect port hover lookup with leeway.
  - Replaced laggy timer-interpolated rack scrolling with direct native wheel scrolling for instant responsiveness.
  - Debounced patchbay minimap scene updates via a single coalescing timer to eliminate cascade redraws during node manipulation.
  - Throttled sub-pixel rubberband marquee updates to reduce scene collision testing overhead.

## [1.1.5] - 2026-10-28

PipeWire patchbay nodes restoration and side-by-side split rendering fix.

### 2026-10-28 05:35:00
- **fix(audio)**: detect active PipeWire sessions and PipeWire-JACK paths for default JACK driver
  - On PipeWire systems where `pw-jack` or standalone `jackd` binaries are not in `/usr/bin` (e.g. Bazzite / Fedora Atomic, clean minimal installs), Clara previously fell back to `PulseAudio`, preventing system and application PipeWire audio nodes from appearing in the patchbay.
  - In [carla_shared.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_shared.py), check for `$XDG_RUNTIME_DIR/pipewire-*` sockets, `ctypes.util.find_library("jack")`, and distro-specific PipeWire JACK paths so PipeWire systems reliably initialize with the JACK engine driver.
  - In [build_appimage.sh](file:///home/acroarch/Documents/Projects/git-clones/Carla/scripts/build_appimage.sh), append distro PipeWire-JACK library search directories to `LD_LIBRARY_PATH` inside `AppRun`.
- **fix(patchbay)**: show external PipeWire/JACK nodes by default and remember Show External/Internal state
  - In [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py), `slot_handleEngineStartedCallback` previously forced `fExternalPatchbay = False` whenever Process Mode was set to Patchbay, hiding all PipeWire graph nodes unless the user manually toggled Canvas -> Show External.
  - Added `CARLA_KEY_CANVAS_SHOW_EXTERNAL` to remember the user's choice across restarts, defaulting to `True` so PipeWire patchbay nodes appear immediately.
- **fix(ui)**: prevent transparent viewport smear in side-by-side split mode
  - In [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py), `QTabWidget::pane` background was transparent, allowing the window frame to show through behind the plugin rack list and smearing graphics during movements. Set background-color to match the canvas background.

## [1.1.4] - 2026-10-25

Window lifecycle & system tray stability release: closing plugin edit windows no longer terminates the host engine, and minimize-to-tray works reliably under tiling Wayland/X11 compositors.

### 2026-10-25 06:10:00
- **fix(ui)**: prevent closing or killing plugin edit windows from terminating backend host engine and restore tray minimize reliability
  - In [carla_widgets.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_widgets.py) and [carla_skin.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_skin.py), closing a plugin edit window or slot triggered `host.engine_close()` on timer cleanup from legacy standalone test code, crashing the entire Clara host process when closed via window managers or kill commands.
  - Guarded `engine_close()` to only execute in standalone test harness (`parent is None`), and updated `editDialogVisibilityChanged` when closing the edit dialog.
  - In [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py), provided explicit SVG resource and theme fallbacks for `QSystemTrayIcon` when `windowIcon()` is null so waybar / StatusNotifierItem displays the icon, and made `_minimizeToSystemTray()` execute synchronously in `closeEvent` before compositor window destruction.

## [1.1.3] - 2026-10-22

Patchbay toolbar feedback release: the floating tool palette now shows which toggles are enabled, and a manually created cable is drawn instantly instead of fading in.

### 2026-10-22 12:55:00
- **fix(ui)**: canvas toolbar toggles now show their "on" state, and manually created cables appear instantly
  - The floating patchbay tool palette (signal flow/pulses, grid, snap and the pointer/select/hand modes) looked exactly the same whether a toggle was enabled or disabled, so there was no way to tell that the animated signal flow was actually running.
  - Root cause: the live stylesheet is compiled by the theme engine from [base_primitives.qss](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/base_primitives.qss) alone. The per-theme rules in `source/frontend/styles/themes/*.qss` - which do contain a `:checked` rule for the tool palette - are never loaded, because the theme registry always resolves a theme definition and the engine path takes precedence over the static-file fallback. Those four files were effectively dead code.
  - [base_primitives.qss](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/base_primitives.qss): now carries the floating tool palette rules (panel surface, flat buttons, hover and an accent `:checked` state), so every theme - Catppuccin Mocha/Macchiato/Latte, Classic Dark, Nord, Tokyo Night, Dracula and Gruvbox Dark - highlights the enabled toggles.
  - [patchcanvas.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/patchcanvas/patchcanvas.py) and [utils.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/patchcanvas/utils.py): a cable created by manually connecting two ports no longer fades in over 750ms, it is drawn immediately. `CanvasItemFX()` takes an optional duration, so the eye-candy fade is untouched everywhere else (node and port appearance, cable removal).

## [1.1.2] - 2026-10-22

Patchbay focus and packaging release: the focused node title stays readable, cables react to focus immediately, and the AUR `clara-bin` package builds, installs and updates correctly.

### 2026-10-22 11:05:00
- **fix(ci)**: the published AUR `pkgrel` counter is no longer reset on every release
  - The release job copied `aur/clara-bin/PKGBUILD` verbatim and rewrote only `pkgver`, which reset the published AUR `pkgrel` back to the repository base value. The sync workflow derived the counter from the repository copy as well, so a second packaging change could not increment it past the already published value.
  - Both workflows now treat the AUR counter as the source of truth: it is kept when only the version changed, incremented when the PKGBUILD content changed, and never moves backwards. The sync workflow also never publishes a version whose release assets do not exist yet, so a packaging fix can no longer point users at a download that has not been released.

### 2026-10-20 05:55:00
- **fix(aur)**: `clara-bin` AUR package no longer fails to build
  - Users reported "Doesn't install on arch" for `clara-bin`. The upstream release asset (`clara-bin-<ver>-<rel>-x86_64.pkg.tar.zst`) is itself a pacman package and therefore carries pacman's own metadata files; the AUR `package()` step stripped `.PKGINFO` and `.MTREE` but left `.BUILDINFO` in the package root, so makepkg aborted with `ERROR: Dotfile found in package root` and no package was ever produced.
  - [aur/clara-bin/PKGBUILD](file:///home/acroarch/Documents/Projects/git-clones/Carla/aur/clara-bin/PKGBUILD): `.BUILDINFO` is now excluded as well, so the AUR build completes and the resulting package installs and runs (`Clara v1.1.1`).
  - The same PKGBUILD derived the release asset name from `${pkgrel}`, but the release workflow always builds the Arch asset with `pkgrel=1`, so bumping the AUR `pkgrel` (as AUR requires when the PKGBUILD changes) made the download 404. The upstream release counter is now a separate `upstream_rel` variable.
  - The upstream release binaries are already stripped and carry no debug info, so makepkg's strip/debug pass only produced `No debugging symbols` warnings from `gdb-add-index` plus an empty `clara-bin-debug` split package. The PKGBUILD now uses `options=('!strip' '!debug')`, so the build is clean and only one package is produced.
  - Added [.github/workflows/aur-sync.yml](file:///home/acroarch/Documents/Projects/git-clones/Carla/.github/workflows/aur-sync.yml), a manually triggered workflow that syncs the in-repo PKGBUILDs to the AUR repositories (bumping `pkgrel` when the PKGBUILD changes), so packaging fixes reach users without waiting for a full release cycle.

### 2026-10-20 05:30:00
- **fix(patchbay)**: focused node name no longer disappears, and cables react to focus immediately
  - Two issues reported from the Reddit release thread: "when a sink is focused, the sink's name disappears" and "manual linking is not automatically initiated until the chosen sink is moved to a new position".
  - [theme.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/patchcanvas/theme.py): the app-theme adaptation mapped the selected node title to `bg-primary` (the canvas background) while the title is drawn on the header background (`bg-surface`). On any dark palette those two are nearly identical shades, so the title vanished the moment the node was focused. The selected title now uses the accent color, and `parse_theme_dict()` runs a contrast pass on `box_text_sel` against the header background so the name stays readable on every theme.
  - [canvasbox.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/patchcanvas/canvasbox.py): `CanvasBox.itemChange()` now handles `ItemSelectedHasChanged` and calls the new `updateConnectionSelectionState()`, which refreshes the selection state of the attached cables. Focusing a node highlights and re-routes its cables immediately, instead of only after the node is dragged to a new position.

## [1.1.1] - 2026-10-20

Stability and reliability patch: Cardinal crash-on-load fix, Add Plugin view sync, persistent plugin cache, single startup recovery prompt, and a filetype-agnostic storage refactor.

### 2026-10-20 04:45:00
- **refactor(storage)**: program is now filetype-agnostic; only the save manager knows extensions
  - Project files, plugin state files and autosaves were recognized by hard-coded `.carxp`/`.carjp`/`.json`/`.carxs` string checks scattered across the host, widgets, session manager and rack list. The program now carries a filename plus an opaque format *tag*, and every extension/format decision lives in `ProjectStorageManager`.
  - [project_storage.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/project_storage.py): `ProjectStorageManager` is now registry-driven (`ProjectFormat` entries for XML project, JSON project, state). Added format-agnostic helpers `get_project_root()` (returns a common XML root for any project), `is_project_file()`, `is_state_file()`, `tag_from_filter()`, `ensure_extension()`, `open_filter()`/`save_filter()`, `sidecar_positions_path()`/`has_sidecar_positions()`. `is_project_file()` trusts primary extensions but only treats legacy `.json`/extension-less files as projects after content validation, so unrelated JSON on disk is never mistaken for a session. Legacy `*.json` stays loadable but is kept out of the file-dialog filters.
  - [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py): bridge pre-check, sidecar lookup, recent-projects, file tree double-click, NSM open and the open/save dialogs now route through the manager; save-as derives the extension from the selected filter tag instead of string matching.
  - [project_session.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/project_session.py): autosave discovery and JSON-vs-XML handling use `is_project_file()` and `prepare_for_backend_save()`.
  - [carla_widgets.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_widgets.py) / [racklistwidget.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/widgets/racklistwidget.py): plugin state dialogs and drag-drop project detection use the manager.

### 2026-10-20 04:15:00
- **fix(startup)**: single prompt for last-save/autosave recovery, loaded under the last-saved name and path
  - Startup could show two prompts back to back: a "Autosave Recovery Detected" `QMessageBox`, then the "Recent Session" offer dialog. These are now a single dialog: when a newer autosave exists the offer switches to a "Recover Session" presentation and the autosave content is loaded while the project keeps its last-saved name and path (`fProjectFilename`), so saving writes back to the real project.
  - [carla_widgets.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_widgets.py) `ProjectLoadingDialog`: added `recover_mode` and `offer_detail` options (title "Recover Session:", "Recover Session" button, custom detail text/height); non-offer usage unchanged.
  - [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py) `checkRecentOnStartup` no longer shows the separate recovery prompt; it passes the recovery info to the one dialog. `loadProjectNow` now records the actual loaded source so `projectLoadingFinished` restores canvas positions from the recovered autosave rather than the older project file.

### 2026-10-20 04:00:00
- **fix(pluginlist)**: cache every plugin format so a restart no longer needs a full rescan
  - The native discovery reports LV2 and internal plugins with a null `sha1` (`PluginDiscovery.cpp`), and both the scanner and dialog only wrote cache entries when a `sha1` existed. As a result LV2 (444) and internal (28) plugins were never cached and were re-enumerated on every launch, so the Add Plugin list looked incomplete until a manual refresh.
  - [startup_scanner.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/startup_scanner.py): added `_cacheKeyFor()` which falls back to a stable synthetic key derived from the plugin identity (`build|type|uniqueId|filename|label|name|maker`) when no `sha1` is available; the scanner now caches all formats and replaces (rather than appends to) an entry on first write per run, preventing duplicates for formats the native cache callback cannot skip.
  - Added a post-scan `_prunePluginCache()` pass that removes stale entries: synthetic entries whose plugin type was fully enumerated this run but not rewritten (plugin removed or identity changed), and sha1 entries whose filename now hashes differently (plugin updated). Formats skipped this run are left untouched to avoid wiping cache when a path is temporarily disabled.

### 2026-10-20 03:30:00
- **fix(pluginlist)**: Add Plugin dialog rack/cards no longer add the wrong plugin
  - The table auto-sorted itself with Qt (`sortByColumn`/`setSortingEnabled`) while the Rack and Cards lists stayed in insertion order. Every cross-view operation is keyed by row index, so once the table was sorted a rack/card row pointed at an unrelated plugin. The table now uses custom sorting (`_sortInfos`/`_onHeaderClicked`) that rebuilds all three views in the same order, restoring correct add, selection, favorite toggle, info panel and filtering.
  - [pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py): disabled Qt built-in table sorting, sort column/order is persisted via the header state, streamed scan results are appended in order and fully re-sorted when the scan finishes, and `_startScan(ignoreCache=True)` now clears the rack/cards lists too.

### 2026-10-20 03:00:00
- **fix(plugins)**: prevent the Cardinal VST3 crash (`X_GLXMakeCurrent` BadAccess + SIGSEGV) by sandboxing
  - Cardinal (VCV Rack) creates its own OpenGL/GLX context; when loaded in-process it collides with the host's GL context on the X server and takes Clara down. It is now auto-bridged when added, and included in the project-load bridge pre-check alongside KV-Element/JUCE.
  - [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py) `loadPluginFromData` forces `PLUGIN_OPTION_USE_BRIDGE` for Cardinal unless the user picked an explicit bridge mode; `loadProjectNow`'s collision pre-check now matches `cardinal` (and treats a missing `PreferPluginBridges` entry as "bridges off").

### 2026-10-19 23:45:00
- **docs**: refresh TODO.md and the README roadmap for shipped work; replace the last HTML dash entities

### 2026-10-19 23:30:00
- **docs**: replace long dashes (em/en) with standard hyphens across docs, comments, and CI output

### 2026-10-19 23:20:00
- **docs**: punctuation cleanup in the new README/CONTRIBUTING text

### 2026-10-19 23:10:00
- **docs**: add a "Why Clara?" section to the README
  - Explains Clara's frontend/QoL focus (patchbay ergonomics, OpenGL-driven animations, toggleable visuals) while crediting upstream Carla as the OG engine it builds upon.

### 2026-10-19 22:50:00
- **docs**: document the v1.1.0 CLI experience and the release version guard
  - [README.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/README.md) gained a "Modern CLI Experience" section covering the rich startup banner and the Ctrl+C prompt.
  - [installation.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/installation.md) AppImage/Flatpak examples bumped to 1.1.0 and the new launch/CLI behaviour documented.
  - [CONTRIBUTING.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/CONTRIBUTING.md) gained a "Release Process" section describing the tag/version consistency check, `scripts/check_version.sh`, and `scripts/release_and_push_aur.sh`.
  - [TODO.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/TODO.md) now tracks the finished CLI banner/SIGINT work.

## [1.1.0] - 2026-10-19

### 2026-10-19 22:20:00
- **feat(cli)**: rich startup banner and rich Ctrl+C prompt
  - Starting Clara from the CLI now prints a rich panel reading "Clara vX.Y.Z" then "based on Carla version A.B.C" (plus Python/Qt/PyQt/paths) instead of the plain `Carla ... started, status:` lines; `--version` uses the same banner. Falls back to plain text when `rich` is unavailable ([carla_shared.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_shared.py) `printStartupBanner`, called from [carla_host.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_host.py)).
  - The terminal SIGINT (Ctrl+C) prompt is now a rich panel: pressing `Enter` quits (default) and `T` keeps Clara running in the system tray, with a plain-text fallback.

### 2026-10-19 21:45:00
- **ci(release)**: enforce tag/version consistency and fix the AUR push on release
  - Added [check_version.sh](file:///home/acroarch/Documents/Projects/git-clones/Carla/scripts/check_version.sh) which verifies a pushed `vX.Y.Z` tag matches `base_version` in [carla_shared.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_shared.py) and the `latest`/entry in [releases.json](file:///home/acroarch/Documents/Projects/git-clones/Carla/releases.json); the AUR `pkgver` is checked as a warning since CI bumps it.
  - Added a `version-check` job to [package.yml](file:///home/acroarch/Documents/Projects/git-clones/Carla/.github/workflows/package.yml) that gates `release`/`publish-aur` on tag pushes, and gave the release checkout `fetch-depth: 0` so `git push HEAD:main` fast-forwards instead of being rejected by the shallow clone.
  - The [pre-push hook](file:///home/acroarch/Documents/Projects/git-clones/Carla/scripts/git-hooks/pre-push) now runs the version check on `v*` tag pushes and blocks a mismatched tag (override with `CLARA_SKIP_VERSION_CHECK=1`).
  - [release_and_push_aur.sh](file:///home/acroarch/Documents/Projects/git-clones/Carla/scripts/release_and_push_aur.sh) now also bumps `base_version`, which had drifted and made packages self-report the wrong version to the in-app updater.

## [1.0.5] - 2026-10-19

### 2026-10-19 21:15:00
- **fix(version)**: bump the internal Clara version fallback to 1.0.5
  - `_get_clara_version()` in [carla_shared.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_shared.py) still returned `"1.0.3"` when no exact tag could be resolved (i.e. installed builds without a `.git` checkout, such as the AUR source tarball).
  - This drives `CLARA_VERSION_STRING`, which the About dialog, `setApplicationVersion`, and the update checker read, so a 1.0.4 package reported 1.0.3 and the updater kept re-offering the current release.

## [1.0.4] - 2026-10-19

### 2026-10-19 20:45:00
- **feat(plugins)**: choose bridge mode (in-process vs sandboxed) when adding a plugin
  - Added a "Mode:" selector in the plugin add dialog ([pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py)) with `Default`, `In-process (inline display)` and `Bridged (sandboxed)` choices, so a single plugin can opt out of (or into) the global bridge preference at add time.
  - Introduced `PLUGIN_OPTION_USE_BRIDGE` (`0x800`) and `PLUGIN_OPTION_AVOID_BRIDGE` (`0x1000`) in [CarlaBackend.h](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/backend/CarlaBackend.h) and [carla_backend.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_backend.py), honored per-plugin in [CarlaEngine.cpp](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/backend/engine/CarlaEngine.cpp) on top of the global `PreferPluginBridges` option.
  - The choice is persisted with the plugin in the project `<Options>` value and re-applied on load and clone, so in-process plugins keep rendering their inline displays in the patchbay while sandboxed plugins stay bridged.

### 2026-10-19 19:30:00
- **feat(settings)**: expose plugin-bridge controls in the data-driven settings UI
  - Added a "Plugin Sandboxing & Bridges" set of controls to [settings_schema.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/settings_schema.py): an "Enable plugin bridges (experimental)" master checkbox (`Experimental/PluginBridges`) and a "Run plugins in bridge mode when possible" checkbox (`Engine/PreferPluginBridges`), restoring the control that was missing from the schema-driven Experimental tab.
  - The bridge-mode checkbox depends on the master toggle and includes a tooltip noting that bridged plugins cannot show inline displays and that an engine restart is required.

### 2026-10-19 18:50:00
- **fix(patchbay)**: restore inline display rendering and dimensions for VU meters inside node boxes
  - Fixed configuration scope in [carla_settings.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_settings.py) by targeting `QSafeSettings("falkTX", "Carla2")` so `Canvas/InlineDisplays` properly persists and synchronizes to `patchcanvas.options.inline_displays`.
  - Accounted for node header and rack subbar heights in [canvasbox.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/patchcanvas/canvasbox.py), ensuring embedded plugin inline displays (like Big Meter and LV2 utilities) reserve sufficient canvas box dimensions and align properly beneath toolbar controls.

### 2026-10-19 17:36:00
- **fix(ui)**: restore search field and filter visibility across all view modes
  - Fixed search and filter regression in [pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py) where rows passing filter checks were accidentally not unhidden due to an omitted `_showRow(i)` call.
  - Re-synchronized `_hideRow` and `_showRow` to update Table, Rack, and Cards rows consistently without desync when filtering.
  - Completely removed the 12ms background streaming timer that was forcing thousands of complex `CardPluginItemWidget` QFrames to be allocated in RAM.
  - Replaced bulk card allocation with pure on-demand viewport rendering via `viewport().indexAt(QPoint(...))` so only currently visible cards on screen are ever created.
  - Restricted widget creation and `updatesEnabled` toggling exclusively to the active view mode (Rack or Cards) rather than populating and hiding all three views in parallel.
  - Added on-demand view visibility synchronization `_syncViewModeVisibility()` when toggling view modes, avoiding redundant hidden-state loops during search and filter operations.
  - Fixed `TypeError: cannot use 'PyQt6.QtWidgets.QListWidgetItem' as a set element` in [pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py) by iterating selection lists directly.
  - Fixed exponential path list duplication bug in [carla_settings.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_settings.py) by clearing `lw_*` list widgets before loading and deduplicating stored paths.
  - Fixed duplicate plugin streaming in [pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py) by returning `False` on duplicate in `_pluginsAdd()`, preventing duplicate table rows from being added.
  - Added discovery stage logging and imported `log_carla` in [startup_scanner.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/startup_scanner.py).
  - Fixed missing `QTimer` import in [carla_settings.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_settings.py).

### 2026-10-19 17:28:00
- **fix(ui)**: transparent plugin card text backgrounds and debounced live theme switching in settings
  - Enforced `background: transparent` and `setAutoFillBackground(False)` on all text labels within `CardPluginItemWidget` in [pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py) and [base_primitives.qss](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/base_primitives.qss), eliminating opaque rectangular background boxes on plugin cards.
  - Added a 120ms single-shot timer debounce to live theme selection in [carla_settings.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_settings.py), decoupling rapid combobox navigation from blocking whole-app stylesheet re-evaluations and icon re-rendering.

### 2026-10-19 17:10:00
- **fix(styles)**: eliminate opaque text background blocks in rack slots for clean color tinting
  - Enforced `background: transparent` across all rack item text labels, title stacks, and sub-containers in [carla_skin.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_skin.py) and [base_primitives.qss](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/base_primitives.qss).
  - Disabled `autoFillBackground` on rack slot title and badge labels so custom category color tints render cleanly and flatly without opaque rectangular seams.

### 2026-10-19 14:50:00
- **fix(styles)**: achieve end-to-end theme compliance across rack slots, patchbay canvas background, typography, and pills
  - Fixed typography clipping across rack slots and controls by setting `font-family: inherit` in [engine.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/engine.py), honoring system font metrics and optical font advances.
  - Bound [carla_skin.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_skin.py) rack items to active theme tokens via `get_active_skin_palette()`, preserving custom color tinting while synchronizing background, text, sliders, and borders with the chosen theme.
  - Linked [patchcanvas/theme.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/patchcanvas/theme.py) to active engine tokens (`bg-primary`, `bg-surface`, `accent`, `border-dim`), harmonizing the canvas background color with the application theme.
  - Upgraded filter sidebar pills in [pluginlistdialog_py.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/pluginlistdialog_py.py) to dynamically bind to `--accent`, `--bg-surface`, `--border-dim`, and `--text-secondary`.

### 2026-10-19 14:37:00
- **fix(settings)**: resolve groupbox title overlaps and synchronize sidebar icon colors with active theme
  - Re-anchored `QGroupBox` and `QGroupBox::title` styles with `subcontrol-origin: margin`, `margin-top: 14px`, and proper padding in [base_primitives.qss](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/base_primitives.qss), eliminating chopped titles and overlapping widget content.
  - Linked `_make_glyph_icon` directly to the active theme engine accent token with fallback to `QPalette.Highlight`, and added `_update_sidebar_icons()` on theme switching in [carla_settings.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/carla_settings.py).

### 2026-10-19 14:24:00
- **feat(styles)**: centralize theming engine with Base16/Base24 ingestion, auto light/dark flip, and unified UI primitives
  - Implemented deterministic cascade pipeline in [engine.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/engine.py): `System Core Defaults` -> `Semantic Variable Map` -> `Active Theme Overrides (Palette)` -> `Mode Inversion (Light/Dark)` -> `Component Primitives`.
  - Built comprehensive root baseline [base_primitives.qss](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/base_primitives.qss) binding variables to headers, buttons (`.btn`, `.btn-primary`, `.btn-subtle`, `.btn-danger`), pills/badges (`.pill`), form inputs, cards, rack items, tables, and minimal scrollbars.
  - Implemented direct Base16/Base24 palette ingestion and automatic grayscale scale flipping (`base00`-`base07`) for instantaneous light/dark modes without altering accent colors.
  - Consolidated theme definitions into a centralized registry [registry.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/registry.py) bundled with lean Base16 palettes (Catppuccin Macchiato, Mocha, Latte, Classic Dark, Nord, Tokyo Night, Dracula, Gruvbox Dark) and dynamic YAML/JSON ingestion.
  - Integrated [ThemeEngine](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/engine.py) into [ThemeManager](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/theme_manager.py) and added verification demo [demo_theme_verification.py](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/styles/demo_theme_verification.py).

### 2026-10-19 14:16:00
- **feat(pluginlist)**: achieve 1:1 visual parity with generative UI redesign
  - Upgraded `QFrame#rackPluginItem` to 10px rounded capsule aesthetics, increased spacing, and polished category accent indicator bars.
  - Upgraded `QFrame#cardPluginItem` to 12px rounded cards with 10px top accent strips, subtle horizontal divider lines, developer subtitle coloring, and proper pill margins.
  - Replaced native OS checkbox with crisp golden text stars (`★` / `☆`) in `QTableWidget` favorite column.
  - Added transparent item selection background stylesheets to `pluginRackListWidget` and `pluginCardsListWidget` to eliminate Qt's native selection overlay fringe and allow custom card borders to shine.
  - Styled `QTableWidget` rows with subtle bottom borders, 30px height, and refined selection highlights across all 4 themes.
- **fix(pluginlist)**: eliminate required scroll to render cards/rack items and colorize format badges
  - Fixed issue where the user had to scroll first before cards or rack items visually appeared by adding `_ensureVisibleWidgets()` to eagerly instantiate the active viewport batch on `showEvent`, filter changes, and view mode switching.
  - Replaced fallback `indexAt()` scroll detection with direct scrollbar offset calculation (`sb.value() // rowHeight`), ensuring rock-solid row range coverage during fast or fractional scrolling.
  - Enhanced `RackPluginItemWidget` and `CardPluginItemWidget` with distinct format pill colors (CLAP, VST3, LV2, VST2, JSFX), custom amber favorite stars, and set default table row height to 30px for better vertical rhythm.
- **feat(pluginlist)**: optimize dialog cold start to ~50ms, modernize cards and rack items, and style table headers
  - Implemented on-demand lazy/streaming instantiation for Rack and Card item widgets, reducing cold-start modal freeze from ~1,529ms to ~50ms (>30x speedup) across 800+ plugins.
  - Added background chunk streaming timer and scroll event hooks (`_onRackScroll`, `_onCardsScroll`) to populate visible viewport rows smoothly on demand.
  - Modernized `CardPluginItemWidget` geometry (190x115px, `border-radius: 8px`), top 4px category accent color strip with rounded corners, formatted I/O labels (`Stereo`, `Mono`, `MIDI`), and pointing hand cursor on favorite stars.
  - Modernized `RackPluginItemWidget` with category accent indicator, clean typography hierarchy, and selection highlight states.
  - Added dedicated styling for `QHeaderView`, `QHeaderView::section`, and `QTableCornerButton::section` across all four QSS themes (`catppuccin_macchiato.qss`, `catppuccin_mocha.qss`, `catppuccin_latte.qss`, `classic_dark.qss`).
- **feat(pluginlist)**: simplify reset filters button, combine view modes into single toggle, and split rescan into two buttons
  - Simplified the Reset Filters button into a flat, compact action with subtle styling and clean 16px icon.
  - Converted the 3-button segmented Rack/Cards/Table switcher into a single cycling toggle button (`btnViewMode`) displaying the active mode glyph and title (`☲ Rack`, `▦ Cards`, `☰ Table`).
  - Separated the rescan toolbutton popup into two explicit push buttons: `Rescan` (quick incremental scan) and `Full Rescan` (complete cache-busting discovery).

### 2026-10-19 13:32:00
- **fix(pluginlist)**: harmonize pill filter button geometry and rounded capsule border radii
  - Fixed distorted dimensions and square corners on selected filter pills by synchronizing `border-radius: 12px`, `padding: 2px 9px`, `min-height: 20px`, and `max-height: 20px` across both normal and `:checked` states in `filterSidebar` and all 4 QSS themes.
  - Eliminated size jumping and layout collapse on "All" master pills and format/type/arch filter pills when toggling selection.

### 2026-10-19 13:21:00
- **fix(pluginlist)**: use system highlight color for selected filter sidebar pills
  - Replaced hardcoded blue tones in all 4 QSS themes (`catppuccin_macchiato.qss`, `catppuccin_mocha.qss`, `catppuccin_latte.qss`, `classic_dark.qss`) with dynamic `palette(highlight)` and `palette(highlighted-text)`.
  - Added scoped dynamic stylesheet injection in `PyPluginListDialog._buildFilters()` to bind `QPushButton[pill="true"]:checked` to `QPalette.Highlight` and `QPalette.HighlightedText`, ensuring identical visual accent color to the Settings sidebar.

### 2026-10-19 13:12:00
- **fix(settings)**: import missing `QApplication` and `QPalette` in `carla_settings.py`
  - Resolved `NameError: name 'QApplication' is not defined` when opening the Carla Settings dialog (`slot_configureCarla`).

### 2026-10-19 06:47:00
- **fix(ui)**: complete 4-theme QSS parity, style plugin browser presentation modes, and fix selection collisions
  - Achieved 100% selector parity across all 4 themes (`catppuccin_latte.qss`, `classic_dark.qss`, `catppuccin_macchiato.qss`, `catppuccin_mocha.qss`), adding complete styling for checkboxes, radio buttons, combo box popups, text edits, sliders, tab bars, and item views.
  - Resolved objectName collision on `list_rack` in Add Plugin dialog (`pluginRackListWidget`), ensuring items render with proper card background, borders, and hover/selection highlights instead of host rack transparent defaults.
  - Enclosed `Rack`, `Cards`, and `Table` view mode buttons into a segmented container frame (`#viewModeContainer`) matching the prototype UI.
  - Added dynamic item-level selection updates for `RackPluginItemWidget` and `CardPluginItemWidget` (`[selected="true"]`).
  - Converted favorite stars to theme-adaptive QSS property styling (`QLabel#itemStar[starred="true"]`) and replaced hardcoded hex colors on settings helper text with `QLabel[role="help"]`.

### 2026-10-19 06:30:00
- **refactor(logger)**: filter background noise and demote repetitive bridge/engine/scanner logs to DEBUG
  - Expanded `CarlaLogger` benign noise rules to catch high-frequency Sfizz CC parameter queries, CLAP extension checks, and Wine/yabridge driver probing.
  - Demoted yabridge multiline banner messages (`[AlterEgo-...]`, hosting mode, bitbridge features) to `DEBUG` under the `[BRIDGE]` tag.
  - Categorized repetitive non-fatal backend assertions (`size > 0`, `! pData->loadingProject`, `var.size >= size`, `urid < fCustomURIDs.size()`), unsupported KVT item notices, and scanner batch status logs to `DEBUG`.
  - Demoted nested CLAP host / JUCE rack constructor chatter and plugin latency query warnings to `DEBUG`.
  - Demoted Wayland text input surface warnings, FreeType glyph errors, and Qt SVG/font setPixelSize warnings to `DEBUG`.
  - Filtered background plugin scanner discovery lines (`[CLAP Scanner] Found:`) and SHM temp retries from polluting the standard info log.
  - Replaced lingering raw `print()` calls in `carla_host.py` with structured `log_carla()` and `logger` calls.

### 2026-10-19 06:24:00
- **refactor(logger)**: clean up dirty log spam and categorize benign callbacks to DEBUG
  - Demoted high-volume engine callbacks (`PATCHBAY_CLIENT_ADDED/REMOVED/RENAMED`, `slot_handlePluginAddedCallback`, port mappings) to `DEBUG` level.
  - Expanded `CarlaLogger.log_raw_string` benign noise filters to capture Qt platform/icon warnings (`kf.iconthemes`) and internal discovery checks.
  - Replaced unformatted `print()` calls in canvas connections, project session autosave, and plugin list dialog with structured `log_carla()` calls.

### 2026-10-19 06:14:00
- **style(pluginlist)**: compact capsule styling for filter pills
  - Reduced filter pill padding to `2px 7px` and font size to `10px` for tighter spatial density.
  - Increased pill border-radius to `9px` (capsule shape) across all Catppuccin and Classic Dark stylesheets and prototype HTML.

### 2026-10-19 06:10:00
- **feat(pluginlist)**: added 3 center browser presentation modes (Rack, Cards, Table) and high-visibility pill highlights
  - Implemented 3 switchable center presentation modes via `QStackedWidget`: **Rack Mode** (new default sleek horizontal capsule slots with category color strips, favorite stars, and I/O tags), **Cards Mode** (modular responsive grid cards), and **Table Mode** (classic sortable `QTableWidget`).
  - Added 3-button mode switcher in the search header with preference persistence in `PluginDatabase/ViewMode`.
  - Maintained 1:1 bidirectional selection, favorite starring, and filter synchronization across all three presentation modes.
  - Upgraded selected pill highlights across all theme stylesheets (`catppuccin_mocha.qss`, `catppuccin_macchiato.qss`, `catppuccin_latte.qss`, `classic_dark.qss`) and prototype HTML to vibrant high-contrast filled accent pills (`#1e66f5`/`#1976d2`, bold white text `#ffffff`, 2px accent border).
- **feat(pluginlist)**: modernized Add Plugin browser with grouped multiselect pill filters and card-based inspector
  - Added [SPEC_ADD_PLUGIN.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/pluginlist/SPEC_ADD_PLUGIN.md) detailing UI parity matrix and interaction spec.
  - Replaced legacy `QToolBox` accordion with a dedicated left filter sidebar containing grouped checkable `QPushButton` pills for Format, Type, Category, Architecture, and Requirements.
  - Implemented bidirectional `[All]` / `[Any]` toggle logic with multi-selection support (union filtering within groups, intersection across groups).
  - Replaced legacy text-label grid in the right pane with a modern card-based Information Inspector featuring structured title/maker card, format badge, architecture, I/O & signals, dynamic requirement tags, and copyable binary path.
  - Refined pill check highlights from harsh solid neon blocks to a polished dark-tinted fill with accent borders and matching typography across all Catppuccin and Classic Dark themes.
  - Relocated Reset Filters to the bottom of the sidebar and added prominent Favorites toggle in the sidebar header.

### 2026-10-19 04:59:00
- **fix(settings)**: bold legible typography for sidebar page navigation tabs
  - Replaced thin 10pt/400-weight sidebar font with bold 11pt typography across all page tabs (General, Patchbay, Engine, OSC, etc.).
  - Increased sidebar item height to 36px and added explicit theme stylesheet rules for crisp legibility.


### 2026-10-19 04:56:00
- **fix(settings)**: optical ink-bounds centering for sidebar tab and action button icons
  - Applied automated pixel-ink bounding box measurement to `_make_glyph_icon` to visually balance all sidebar page tab icons (General, Patchbay, Engine, OSC, etc.).
  - Migrated path action buttons (add, edit, remove, folder) to optically centered `QIcon` instances, removing text-alignment slant.


### 2026-10-19 04:53:00
- **fix(canvas)**: visual and optical centering for floating toolbar glyph icons
  - Introduced `CanvasToolButton` with cached ink bounding-box measurement to eliminate 2-4px horizontal and vertical asymmetry on Nerd Font and unicode glyphs.
  - Render button bevel background and label text in separate passes to preserve native theme states (checked, hover, pressed) while centering glyphs to within 0.5px.
  - Applied visual centering across all canvas navigation toolbar and contextual action toolbar buttons.


### 2026-10-19 04:37:00
- **feat(ui)**: unified recent session prompt and loading dialog with autoload bypass
  - Merged recent session startup prompt (`QMessageBox`) directly into `ProjectLoadingDialog` in-place, eliminating jarring popups and window recreation.
  - Added seamless morphing from session prompt to live progress bar upon clicking "Load Session", with optional "Always load last save on startup" preference checkbox.
  - Automatically bypasses offer screen and initiates direct loading when `--autoload-lastsave` CLI flag or `Main/AutoloadLastSave` setting is active.


### 2026-10-19 04:33:00
- **feat(ui)**: minimal system-framed loading dialog with live plugin and routing status
  - Restored clean native OS window framing to ensure 100% compatibility across all Linux/Wayland/X11 window managers without translucent background artifacts.
  - Streamlined layout to a minimal, compact dialog showing project filename, live completion percentage, and active gradient progress bar.
  - Added specific live loading status updates: detailed plugin names with format tags (e.g. `Surge XT [LV2]`, `Dexed [VST3]`) and audio/MIDI graph routing progress.
  - Kept smooth auto-advancing progress ticker to prevent progress bar freezing during blocking plugin DSOs.
  - Updated Generative UI preview widget to reflect the system-framed minimal style.

### 2026-10-19 04:15:00
- **perf(settings)**: lazy tab building and dialog caching for fast cold start and instant reopen
  - Deferred declarative schema construction for Patchbay, OSC, Wine, and Experimental tabs until explicitly visited, avoiding construction of ~100 widgets on dialog open.
  - Implemented background idle pre-warming (`_prewarmSettingsDialog` via `QTimer.singleShot(400)`) so the dialog is constructed asynchronously before first user interaction, reducing first-click latency from ~150ms to ~0.3ms.
  - Cached `_settingsDialog` on `HostWindow` to eliminate repeated widget instantiation on subsequent settings opens.
  - Moved `getBestNerdFont` to `carla_shared` with set lookup and cached glyph icon rasterization (`_GLYPH_ICON_CACHE`), decoupling settings from canvas imports and preventing FreeType glyph render warnings.
  - Cached discovered theme listings in `ThemeManager` to eliminate repetitive filesystem disk queries.

### 2026-10-19 04:00:00
- **perf(gui)**: visibility culling, OpenGL hardware acceleration, and meter deadband throttling
  - Enabled hardware-accelerated `QOpenGLWidget` viewport on `RackListWidget` to offload rack rasterization from CPU to GPU.
  - Added visibility culling to `HostWindow.idleFast()`, `idleSlow()`, and `AbstractPluginSlot` to skip C++ peak queries and Qt redraws for non-visible slots.
  - Implemented 0.005 delta deadbanding and visibility check in `DigitalPeakMeter.displayMeter` to eliminate redundant repaints.

### 2026-10-19 03:55:00
- **feat(rack)**: pin master Dry/Wet and Volume sliders at the top with distinct accent colors
  - Moved Dry/Wet and Volume sliders to the top of the parameter slider lists in both full and mini slider views.
  - Added Catppuccin Peach/Amber (`#fab387`) accent styling to Dry/Wet and Catppuccin Green/Emerald (`#a6e3a1`) to Volume.
  - Added a clean 1px horizontal separator line between master controls and internal DSP parameters.

### 2026-10-19 02:45:00
- **fix(rack)**: suppress general knobs in slider mode and enable parameter label container scrolling
  - Enforced complete hiding of bottom knob columns (`w_knobs_left` and `w_knobs_right`) in `_reflowResponsiveLayout` while slider mode is active, relying exclusively on dedicated Dry/Wet and Volume sliders.
  - Forwarded mouse wheel scrolling over parameter labels, backgrounds, and whitespace to the active plugin parameter `QScrollArea` instead of scrolling the outer rack.
  - Preserved independent mouse wheel control directly on sliders and spinboxes while removing outer-card wheel hijacking.

### 2026-10-19 02:35:00
- **fix(rack)**: dynamic 5-character minimum width and frameless spinbox line edits
  - Calculated font-metrics-based 5-character minimum width (`"00000"`) and applied it dynamically to both `QDoubleSpinBox` and its inner `QLineEdit`.
  - Set `setFrame(False)` on `QDoubleSpinBox` to strip native frame overhead and removed rigid fixed-width constraints.

### 2026-10-19 02:27:00
- **fix(rack)**: clean borderless parameter readouts and minimum slider travel width
  - Removed borders, outlines, and box backgrounds from `QDoubleSpinBox` for clean, modern DAW-style value text with subtle hover highlight.
  - Expanded value text box width (56px inline, 62px stacked) and height (20px) to eliminate horizontal and vertical digit clipping on multi-digit and decimal values.
  - Enforced 80px minimum width (`setMinimumWidth(80)`) on horizontal parameter sliders to prevent excessive compression.

### 2026-10-19 02:20:00
- **fix(rack)**: compact slider textboxes and dynamic responsive slider card reflow
  - Implemented dynamic `setIsMini` layout switching on `SliderParamWidget` between inline (1-row) and stacked (2-row) card views with `QGridLayout`.
  - In ultra-thin viewports (< 320px), stacked mode gives the horizontal slider 100% full width of the card and places the label and spinbox cleanly on row 1.
  - Compacted `QDoubleSpinBox` dimensions (height 18px, width 40-44px), eliminated hidden subcontrol buttons and internal `QLineEdit` padding, ensuring numerical text is completely readable and unclipped.
  - Dynamically tightened `sliders_layout` margins and spacing in ultra-thin viewports (< 260px).

### 2026-10-19 02:10:00
- **fix(rack)**: isolate knob wheel scrolling and compact responsive knob sizing
  - Implemented `wheelEvent` handling on `CommonDial` and `SliderParamWidget` with event acceptance to directly adjust values without bubbling to the rack list.
  - Intercepted mouse wheel events in `RackListWidget.wheelEvent` over dials, sliders, spinboxes, and comboboxes to prevent rack viewport jumping.
  - Added text elision to `CommonDial.paintEvent` to prevent dial label clipping and overflow in narrow columns.
  - Dynamically scaled dial size (from 58×50px down to 46×44px in `< 260px`) and reduced spacing/margins in `_reflowResponsiveLayout`.
  - Automatically hid secondary right knob column (Dry/Wet/Volume) below 320px width to grant primary plugin controls full breathing room.

### 2026-10-19 01:55:00
- **fix(rack)**: complete 100% visual parity with responsive rack prototype
  - Re-implemented `LEDButton._paintMinimalLed` to paint crisp 1:1 square pixel tiles with specular edge highlights instead of round ellipses.
  - Implemented vertical 2-line Title & Type Stack (`w_title_stack`) with Catppuccin category accents; reflows to dedicated Row 2 in Ultra-Thin mode (`< 230px`) for 100% unclipped title visibility.
  - Updated power and bypass button state stylesheets to emerald green (`#a6e3a1`) and warm amber (`#fab387`).
  - Swapped washed-out legacy 40-50 RGB category colors with vibrant Catppuccin accents for the left rack slot stripe and subtitle.

### 2026-10-19 01:45:00
- **feat(rack)**: unified dynamic adaptive rack slot layout and specification manifest
  - Authored comprehensive specification and parity checklist in `docs/DYNAMIC_RACK_SPEC.md` defining 3 responsive width tiers (Ultra-Thin `< 230px`, Medium `230px-440px`, Wide `≥ 440px`).
  - Decommissioned rigid "Mini Rack Mode" global setting and per-plugin layer toggles in favor of automatic responsive reflow.
  - Implemented universal title double-click to toggle rack slot expansion/collapse across all viewport widths.
  - Enforced strictly square 18×18px 2×2 I/O LED grid with 8×8 square pixel tiles and 18px vertical peak meters.
  - Added stacked parameter card layout (label/value on row 1, 100% width slider on row 2) for narrow sidebars `< 320px` to guarantee full scrub travel and prevent label clipping.
  - Guaranteed 150px+ dedicated breathing room for plugin title in medium viewport by retaining presets on subrow.

### 2026-10-19 01:15:00
- **fix(shortcuts)**: resolve ambiguous `Ctrl+S` and `Ctrl+Shift+S` shortcut overload
  - Removed duplicate `QShortcut` instances that conflicted with window-level `ui.act_file_save` and `ui.act_file_save_as` actions.
  - Set `ApplicationShortcut` context across save, save-as, open, and new actions for seamless window-wide triggering.

### 2026-10-19 01:10:00
- **feat(rack)**: 2-line minified layer layout and scrollable mini parameter drawer
  - Separated slot controls into a clean 2-line flex layout: Row 1 handles power/bypass/type/title and disclosure chevron; Row 2 houses preset selector and LEDs/peak meters to eliminate horizontal widget overlap.
  - Wrapped mini parameter tray in a `QScrollArea` with `MINIMAL_SCROLLBAR_QSS` and standardized label/spinbox column widths (75px/46px), preventing clipping when plugins have many parameters.
  - Adjusted collapsed and expanded slot heights with dynamic scroll handling.

### 2026-10-19 01:05:00
- **fix(patchbay)**: preserve readable text contrast on selected canvasbox nodes
  - Ensured custom tinted headers calculate contrast based on background luminescence rather than being overwritten with inverted/unreadable selection text colors.
  - Safely fell back to standard readable box text when selected text color is unset.

### 2026-10-19 00:50:00
- **feat(rack)**: global mini rack mode setting, unified disclosure button, and cleaned parameter slider layout
  - Added global "Use minified layer view for rack slots by default" setting (`Main/MiniRackMode`) in the Settings dialog Appearance section.
  - Unified the duplicate arrow down / expand button into a single contextual disclosure chevron (`▸`/`▾`/`▴`) that controls both slot collapsing and mini parameter drawer disclosure.
  - Optimized mini parameter sliders spacing, margins, and row height (18px) to stack cleanly without crowding or label overlap.

### 2026-10-19 00:40:00
- **fix(rack)**: fix `get_custom_data_value` method call in `createPluginSlot`
  - Fixed `host.get_custom_data` call which expected a numeric index instead of type and key, causing a traceback when creating plugin slots.

### 2026-10-19 00:15:00
- **feat(rack)**: Photoshop-layer style minified rack view with collapsible mini parameter sliders
  - Introduced minified "Layer View" in `PluginSlot_Minimal` rendering plugins as ultra-compact 36px strips with left-aligned power, bypass, type badge, and title.
  - Added collapsible mini parameters drawer (`w_mini_params_tray`) with disclosure chevron (`▸`/`▾`), exposing essential controls in 18px horizontal mini sliders.
  - Cleaned up layout hierarchy and parenting so toggling between Knobs, Sliders, and Minified Layer views is instantaneous without re-allocating widgets.
  - Added "Minified Layer View" toggle to slot context menu (`slot_showCustomMenu`) and preserved state in plugin custom data (`CarlaSkinLayerMode`).

### 2026-10-18 23:28:00
- **refactor(version)**: centralize Clara version as single source of truth and deprecate unused C++ dialogs
  - Established `carla_shared.py:CLARA_VERSION_STRING` as the single source of truth for Clara versioning with dynamic fallback to git tags.
  - Updated `carla_app.py` to register `CLARA_VERSION_STRING` in `QCoreApplication.setApplicationVersion`.
  - Updated `aboutdialog_py.py` to dynamically display the active Clara version alongside the Carla basis version.
  - Marked superseded legacy C++ dialog files (`aboutdialog.cpp`, `aboutdialog.hpp`, `jackappdialog.cpp`, `jackappdialog.hpp`) as deprecated.

### 2026-10-18 08:38:00
- **fix(shortcuts)**: restore `Ctrl+S` and `Ctrl+Shift+S` save functionality across all focus contexts
  - Fixed missing `QShortcut` and `QKeySequence` import in `carla_host.py`.
  - Registered window-level actions and dedicated `QShortcut` bindings with `Qt.ApplicationShortcut` context so saving triggers even when the menubar is hidden (Modern UI Mode / `Ctrl+M`).
  - Added `Qt.ShortcutContext` compatibility aliases in `qt_compat.py` for PyQt6.
  - Kept project save and open actions active during startup and engine stopped states instead of disabling them.
  - Added `Ctrl+S` / `Ctrl+Shift+S` event interception in `DraggableGraphicsView`, `QGraphicsScene`, and `RackListWidget` to prevent canvas/rack focus from swallowing save events.

### 2026-10-18 08:18:00
- **fix(ui)**: resolve `Qt.WaitCursor` PyQt6 compatibility alias
  - Added `WaitCursor`, `BusyCursor`, `IBeamCursor`, and `ForbiddenCursor` to `qt_compat.py` `Qt.CursorShape` compatibility aliases for PyQt6.
  - Added safe attribute fallback for cursor overrides in `carla_host.py:loadPluginFromData`.

### 2026-10-18 04:40:00
- **feat(plugins)**: non-blocking startup scanner, inline live-streaming refresh, and persistent multi-add loading
  - Added low-priority non-blocking startup background scanner thread (`PluginScannerThread`) to pre-warm plugin cache without audio or UI lag.
  - Replaced secondary refresh modal with inline scan bar featuring live progress, filename status, and instant Stop control.
  - Enabled live incremental streaming of discovered plugins directly into the table while scanning.
  - Implemented multi-selection batch adding (`ExtendedSelection`), "Keep open" toggle, and `Qt.WaitCursor` loading feedback.
  - Optimized search filtering with item-attached precomputed metadata, debouncing, and multi-word `AND` token matching.

### 2026-10-18 04:00:00
- **chore**: synchronize version string to 1.0.3 and ignore local PKGBUILD artifacts

### 2026-10-18 00:50:00
- **feat(theme)**: live system theme adaptation, canvasbox synchronization, and color likeliness matching
  - Implemented `find_closest_system_color` with 75% perceptual likeliness threshold matching and tone adjustment against `QApplication.palette()`.
  - Enabled live seamless toggle of "Use system desktop theme" without application restart, updating the patchbay canvas, canvasboxes, rack background, and top banners in real time.
  - Dynamically synchronized patchbay canvas, canvasbox node headers/bodies, port text, and selection rubberbands to the system palette when system theme is active.
  - Updated rack list widget viewport and top notification/support banners to dynamically adapt to system palette roles.

### 2026-10-18 00:30:00
- **feat(theme)**: Catppuccin Macchiato default, roundedness, minimal scrollbars, and full QSS data-driven styling
  - Set `Catppuccin Macchiato` as default theme for application interface and patchbay canvas.
  - Added modern 6-8px component roundedness and minimal 8px scrollbars with subtle track and contrast hover handles across all themes.
  - Extracted hardcoded inline stylesheets from Python files into theme stylesheets (`catppuccin_macchiato.qss`, `catppuccin_mocha.qss`, `catppuccin_latte.qss`, `classic_dark.qss`) targeting semantic IDs (`#miniCanvasFloatFrame`, `#canvasNodeSearchList`, `#rackListWidget`, `#rackFloatingAddButton`, `#canvasSearchEdit`).
  - Added pure native Qt system theme fallback when "Use system desktop theme" is enabled, clearing inline overrides and restoring the system Qt style.

### 2026-10-17 15:40:00
- **feat(ui)**: data-driven QSS theming engine and theme selector
  - Added `styles/theme_manager.py` discovering and hot-reloading `.qss` theme files dynamically from disk (`source/frontend/styles/themes/` and `~/.config/clara/themes/`).
  - Added Catppuccin Mocha, Catppuccin Latte (Light), and Classic Dark stylesheets.
  - Replaced legacy Pro Theme with `Use system desktop theme` toggle and dynamic `Application theme` selector in Settings > General with live styling updates.
  - Preserved canvasbox and patchbay node/cable theme isolation (`patchcanvas/themes.json`).
- **fix(ci)**: robust version fallback and Fedora RPM version formatting
  - Fall back to numeric tag/version when triggered on branches so `dpkg-deb` and `rpmbuild` do not fail on non-digit branch names.
  - Convert hyphens to dots in RPM `Version:` field to satisfy RPM specification constraints.
- **fix(build)**: install `styles` directory and themes in Makefile
  - Include `styles/` and `styles/themes/*.qss` in `make install` and resource linking so packaged installations find `styles.theme_manager`.

## [1.0.3] - 2026-10-17

### 2026-10-17 11:15:00
- **feat(canvas)**: peak-hold pulse smoothing and gradient-tinted signal flow
  - `pwlevels.py`: implemented 150ms peak-hold buffer with exponential decay (`0.85 ** ((dt - 0.15) / 0.04)`) to eliminate rapid signal flickering and dropouts during transient audio.
  - `canvasline.py`: interpolated RGB colors between source and destination nodes along path parameter `t` (`_interp_color(t)`), rendering cable traveling comets with full source-to-destination gradient tinting.

### 2026-10-17 05:58:00
- **fix(rack)**: eliminate rack width blinking and defocus position jumping
  - Guard `updateRackItemSize()` in `AbstractPluginSlot.resizeEvent` to only trigger when height changes, breaking the re-layout loop between slot frames and `QListWidget`.
  - Maintain symmetric splitter resizing and enforce container `minimumWidth` so Hyprland border adjustments on focus/defocus don't shift the rack rightward.
  - Make statusbar indicators and combo boxes flexible with `QSizePolicy.Ignored` / `Minimum` so the window minimum width drops from 824px to 420px, allowing half-screen tiling without layout clipping.

### 2026-10-17 05:32:00
- **feat(settings)**: declarative schema overhaul with responsive 2-column layout and UI refinements
  - Reconstructed settings tabs (**General**, **Patchbay**, **OSC**, **Wine**, **Experimental**) using data-driven schemas (`settings_schema.py`) and `SettingsFormBuilder`.
  - Fixed sidebar tab label truncation by widening the sidebar navigation table and inheriting the default system UI typography.
  - Eliminated legacy dead whitespace by top-aligning form containers directly at the layout root.

### 2026-10-17 03:25:00
- **feat(canvas)**: Clara 1.0.2 - OpenGL-first canvas rendering and uninterrupted signal flow
  - Default `UseOpenGL` to `true` (with fallback only if Qt reports OpenGL unsupported), ensuring hardware acceleration handles canvas box drop shadows, cable glow, and 25 FPS signal-flow pulses fluidly without artificial software-render throttle profiles.
  - `pwlevels.py`: resolved ctypes `c_void_p` callback pointer unwrap in `_on_stream_read`, allowing PipeWire and PulseAudio audio peaks to reliably drive node pulsing and cable travelling comets; added normalized name matching for audio sources.
  - `carla_logger.py`: rate-limit terminal output to 60 lines/sec when attached to a TTY and only mirror logs when `sys.stdout.isatty()`.
  - `carla_host.py`: batched log flushes every 100ms and capped log buffer at 5000 lines to prevent UI thread lockups under high-frequency backend logging; respect `ModernUiMode` at startup and default to hiding the side panel and meters in modern mode.
  - `carla_canvas.py` & `carla_host.py`: anchored floating canvas mode palette, context toolbar, and minimap to the patchbay container frame so they remain consistently positioned regardless of canvas pan/zoom/resize.
  - `carla_settings.py`: prevented normal settings save from resetting experimental and OpenGL selections, and exposed "Fancy eye-candy" directly in the Canvas tab.

### 2026-10-16 21:32:00
- **fix(frontend)**: modern UI hides the side panel by default, and the canvas toolbars no longer drift
  - Side panel: in Modern UI mode the left sidebar is now off at startup; a stale `ShowSidePanel=true` written by classic-era defaults no longer overrides the modern layout. Enabling Modern UI from Settings also closes the sidebar immediately. Classic mode still defaults to the panel shown.
  - `carla_host.py`: `loadSettings` defaults `ShowSidePanel` to `not modernUi` and forces it off while modern is active; `slot_toggleModernUi` hides the side panel when modern is switched on.
  - Canvas toolbars & minimap: the floating left mode palette, the top context toolbar and the floating minimap were parented to the patchbay viewport and re-centred on every resize; they are now anchored to the patchbay container (the graphics view's parent), pinned to the container's top-left, top-right and bottom-right respectively, so panning, zooming, splitter moves and window resizes keep them in place.
  - `carla_canvas.py`: `CanvasViewportFilter` reparents both overlays to the graphics view's parent; `CanvasToolBarOverlay.reposition`/`CanvasContextToolBarOverlay.reposition` pin to fixed top-left/top-right corners.
  - `carla_host.py`: `_ensureMiniCanvasOverlay`/`_ensureMiniCanvasRestoreButton` reparent the minimap overlay and its restore "Map" button to the patchbay container; `_repositionMiniCanvasFloat` pins them to the container's bottom-right.

### 2026-10-16 21:05:00
- **fix(frontend)**: Modern UI setting is honored at startup
  - `ModernUiMode=true` configs that also had a stale `SideBySideEnabled=false` started classic while Settings > Modern UI stayed checked; only retoggling applied the modern view. Two causes: (1) `loadSettings(True)` runs before the side-by-side action exists, so the modern mode was only restored into the checkbox and never applied; (2) `saveSettings` derived `SideBySideEnabled` from "is the split tab the currently selected tab", which saved `false` whenever another tab was focused on close.
  - `carla_host.py`: save now uses the side-by-side action's checked state; both restore paths treat Modern UI as the master switch (modern on ⇒ side-by-side applied regardless of a stale saved `false`).

### 2026-10-16 20:47:00
- **fix(frontend)**: backend log floods no longer freeze the UI
  - The C++ backend floods the debug callback (JACK `nframes == bufferSize` assertion loop, PipeWire/PulseAudio port add/remove churn). Every line was rendered with `rich` for the terminal (`console_enabled` hardcoded `True`, even with no tty attached) and appended one line at a time to the log `QPlainTextEdit`, each call re-laying-out the whole document. Under flood this consumed ~82% of CPU in the logging pipeline (`_print_terminal` 46.5% + `print` 21.8% + `slot_onLogAdded` 21.2%), pegging the GUI thread at ~96% and freezing the app.
  - `carla_logger.py`: console mirroring now defaults to `sys.stdout.isatty()` so GUI launches skip `rich` rendering entirely; terminal output is rate-limited to 60 lines/sec with a `[console throttled: N lines suppressed]` summary.
  - `carla_host.py`: log lines are batched and flushed once per 100 ms instead of one widget re-layout per line; the log widget is capped at 5000 blocks.
  - Verified with py-spy: CPU drops from ~96% to ~10% (now dominated by normal Qt event-loop + refresh timers), UI stays responsive on the software-raster viewport.

### 2026-10-16 06:10:00
- **perf(canvas)**: automatic software-render performance profile for the patchbay
  - Fresh configs default to `UseOpenGL=false`, which put the patchbay on the software raster path where the fork's eye candy makes it unusable. `setupCanvas` now detects the actual viewport type and sets `patchcanvas.options.software_render`; on that path the canvas drops effects that are GPU-cheap but CPU-brutal: box drop-shadow effects (`canvasbox.py`), the cosmetic cable glow overlay (`canvasline.py`), the animated signal-flow pulse (~25 FPS repaint of every active cable, `carla_canvas.py`), and minimap re-renders (whole-scene second pass, `carla_host.py`). GL users are unaffected.

### 2026-10-16 05:20:00
  - New `publish-aur` job in `package.yml` (runs after `release` on `v*` tags): sets up the AUR SSH key from the `AUR_SSH_PRIVATE_KEY` secret, clones `ssh://aur@aur.archlinux.org/<pkg>.git` for both packages, bumps `pkgver`, regenerates `.SRCINFO` with `makepkg`, commits and pushes. `clara-bin` PKGBUILD comes from the repo (source of truth); `clara-git` PKGBUILD is updated directly in its AUR repo. Skips cleanly when nothing changed.
  - AppImage confirmed release-only: it is uploaded as the `appimage-package` CI artifact and attached to GitHub Releases with the other distro packages; `dist/` is gitignored and nothing is committed to the repo.

### 2026-10-16 04:35:00
- **ci(aur)**: release pipeline now ships a real pacman package
  - `package.yml` archlinux job packages with `makepkg` as a non-root builder using the shared `.github/aur/PKGBUILD.in` template, producing `clara-bin-<ver>-1-x86_64.pkg.tar.zst` with proper `.PKGINFO`/`.MTREE` metadata as the release asset (previously a plain `clara-archlinux-*.tar.zst` DESTDIR tarball). `build-test.yml` now uses the same template instead of an inline heredoc.
  - `aur/clara-bin/PKGBUILD` now consumes the package asset via `bsdtar` extraction (excluding `.PKGINFO`/`.MTREE`) instead of copying a `usr/` tree from the plain tarball.
  - The archlinux release container installs the full runtime dependency list so the PKGBUILD dependency set is validated on every release build.

### 2026-10-16 04:20:00
- **ci(aur)**: build a real pacman package with makepkg in the test workflow
  - New `aur` choice for the `only` dispatch input plus a `build-aur` job: builds the source in an `archlinux:latest` container, then packages it with `makepkg` as a non-root user, producing `clara-bin-<ver>-1-x86_64.pkg.tar.zst` with proper `.PKGINFO` and `.MTREE` metadata (instead of the plain DESTDIR tarball the `distros` job uploads). The job asserts both metadata entries exist and uploads the result as `aur-package`.
  - The build container installs the full AUR runtime dependency list, so the dependency set declared in the PKGBUILD is validated on every run.

### 2026-10-16 04:05:00
- **fix(build)**: stop relying on `which` for tool and interpreter detection
  - `source/Makefile.deps.mk` detected the PyQt6 UI tools with `$(shell which pyuic6)`. Minimal build containers (e.g. `fedora:latest`) do not ship `which`, so `PYUIC6` came out empty, `HAVE_FRONTEND` stayed false and the fedora rpm was built without the entire python frontend (no `clara` launcher, no desktop files, only `carla-single` + libs). Switched `PYRCC5`/`PYUIC5`/`PYUIC6` detection to `command -v`.
  - `data/carla*` launcher wrappers resolved the interpreter with `PYTHON=$(which python3)` and a broken `[ ! -f ${PYTHON} ]` check. On guests without `which` (e.g. minimal arch) `$PYTHON` expanded empty and the shell tried to exec the non-executable `/usr/share/carla/carla`, dying with `line 15: /usr/share/carla/carla: Permission denied`. Switched all nine wrappers to `command -v` + `[ -z "$PYTHON" ]`.

### 2026-10-16 03:40:00
- **fix(rpm)**: stop the fedora rpm from owning shared system directories
  - `.github/workflows/specs/clara.spec` used a catch-all `%files` of `/usr/*`, which made the package claim `/usr/bin`, `/usr/include`, `/usr/lib`, `/usr/lib/lv2`, `/usr/lib/pkgconfig` and `/usr/share` as its own directories. On Fedora these belong to `filesystem`/`lv2`/`pkgconf`, so `dnf install clara-*.rpm` aborted with `file /usr/bin from install of clara-0.0.0-1.fc44.x86_64 conflicts with file from package filesystem-3.18-52.fc44.x86_64`.
  - Replaced the glob with the actual clara payload paths: `/usr/bin/*`, `/usr/include/carla`, `/usr/lib/carla`, `/usr/lib/lv2/carla.lv2`, `/usr/lib/pkgconfig/*`, `/usr/share/carla`.

### 2026-10-16 01:30:00
- **fix(ci)**: make the void-musl build actually link and fail loudly
  - The musl jobs set `LDFLAGS='-lfts $LDFLAGS'` with single quotes, so the literal `$LDFLAGS` was stored; make then expanded it as `$L` + `DFLAGS`, producing `ld: cannot find DFLAGS`. Changed to `LDFLAGS="-lfts $LDFLAGS"` in `build-test.yml`, `package.yml` and `package-aarch64.yml`.
  - The musl build hid failures (`docker ... sh -c` with no `set -e`, and `make | tee` masking make's exit code), so a broken build still uploaded a near-empty tarball as success. Added `set -e` and made `make`'s exit status propagate.
  - Added a `only` dispatch input to `build-test.yml` so a single component (e.g. `void-musl`) can be built and re-tested without running every job.

### 2026-10-16 00:45:00
- **fix(ci)**: build VST frontend stubs on every distro and make the rpm version legal
  - alpine/archlinux/fedora jobs now install the OpenGL + X11 development packages (`mesa-dev libx11-dev libxcursor-dev libxext-dev libxrandr-dev`, `mesa libglvnd libx11 libxcursor libxext libxrandr`, `mesa-libGL-devel libX11-devel libXcursor-devel libXext-devel libXrandr-devel`). `HAVE_DGL` requires `pkg-config --exists gl x11 xcursor xext xrandr`; without it the VST2 plugin stubs (`bin/CarlaRack*`, `bin/CarlaPatchbay*`) are never built and `make install` fails at `install_main`.
  - The test workflow's default version is now rpm-legal (`0.0.0`, no `-`), and the fedora job rewrites `-` to `.` before writing `Version:` in the spec (rpmbuild rejects `Version: 0.0.0-test`).

### 2026-10-16 01:00:00
- **ci(test)**: add `build-test.yml` workflow for downloadable test builds
  - New `workflow_dispatch`-only workflow that builds every platform (alpine, ubuntu, fedora, archlinux, void-glibc, void-musl, nix, appimage, flatpak) and uploads the resulting packages as run artifacts. It never publishes, tags, or attaches anything to a release, so builds can be verified and downloaded locally (`gh run download`) without touching release assets.
  - Adds a per-platform "Detect frontend tooling" step that reports `pyuic6`/`uic6` locations and the `HAVE_FRONTEND`/`HAVE_QT6`/`FRONTEND_TYPE` values from `make -pn` into the run summary, to diagnose the Fedora GUI-less packaging issue.
  - Version string is a dispatch input (`version`, default `0.0.0-test`); `fail-fast` disabled so a single distro failure does not cancel the others.

### 2026-10-16 00:20:00
- **fix(ci)**: correct multi-distro packaging (frontend tooling, versioning, naming)
  - Frontend tooling: install the PyQt6 UI tools the build needs (`pyuic6`, required for `HAVE_FRONTEND`). Ubuntu `.deb` and both AppImage jobs now install `pyqt6-dev-tools`; the void-glibc and void-musl jobs install `python3-pyqt6-devel-tools`; the Fedora spec adds `python3-pyqt6` to `BuildRequires`. Previously these jobs silently produced GUI-less packages (no launcher scripts, desktop files, icons or Python frontend).
  - Packaging: removed the `make install ... || cp -r bin` fallback from every distro and void-musl job, so the stray top-level `bin/` build output is never shipped again.
  - Versioning: `build-void-musl` now sets `VERSION` (it was producing `clara-void-musl-.tar.zst`), and the AppImage is named after the Clara release version (`Clara-<release>-<arch>.AppImage`, honoring a `CLARA_VERSION` override) instead of the engine `VERSION`.
  - `scripts/release_and_push_aur.sh` now normalizes the version argument (strips leading `v`/`V`, dots and whitespace, then validates `X.Y.Z`), preventing malformed tags such as `v.1.0.1`.

### 2026-10-15 23:55:00
- **chore(releases)**: retract all published binary artifacts
  - Removed every uploaded binary asset from the GitHub releases `v0.1.0`-`v1.0.1` (including the malformed `v.1.0.1`), keeping only the auto-generated source archives. All were broken: GUI-less deb/rpm/nix/void packages (missing launcher scripts, desktop files, icons and the Python frontend), a non-starting AppImage (no frontend bundled; hard-coded `/home/runner` build paths), an empty `void-musl` tarball, and `archlinux`/`alpine` tarballs that were plain install trees rather than real `pkg.tar.zst` packages (no `.PKGINFO`/`.MTREE`).
  - Each release body now carries a "RETRACTED - DO NOT USE" notice, and `releases.json` marks every documented release `retracted`. Corrected builds will be published after the packaging fixes land.

### 2026-10-15 23:30:00
- **refactor(frontend)**: replace the Qt-linked native dialogs with pure-PyQt6 implementations
  - `libcarla_frontend` (a Qt C++ shared library) is no longer built or shipped. Its three dialogs - About, Add JACK Application, and the Plugin List browser - are reimplemented in Python under `source/frontend/dialogs/` and `source/frontend/pluginlist/`, using the non-Qt `libcarla_utils` backend for plugin discovery.
  - `CarlaFrontendLib` (`carla_frontend.py`) is now a thin pure-Python shim that keeps the same public API, so `carla_host.py` is unchanged and the app no longer needs a system Qt matching the native build (this fixes the AppImage startup crash caused by the Qt ABI mismatch).
  - Makefile: stop building/installing `libcarla_frontend`, and install the new `dialogs`/`pluginlist` Python packages.

### 2026-10-15 22:40:00
- **perf(packaging)**: shrink the AppImage significantly
  - Switched the bundled `appimagetool` from AppImageKit (gzip squashfs) to the maintained `AppImage/appimagetool`, which defaults to **zstd**, and pinned `--comp zstd --mksquashfs-opt -Xcompression-level 19` (override with `APPIMAGE_ZSTD_LEVEL`).
  - Added a `trim_appdir` pass before packaging: deletes Python test/idlelib/tkinter/`ensurepip`/pip, `__pycache__`/`*.pyc`/`*.pyo`, PyQt6 `*.pyi` stubs, Qt `translations`/`qml`/`lib/cmake`/`lib/pkgconfig`/`lib/metatypes`, `*.a`/`*.la`/`*.prl`, and `include`/`man`/`doc`, then strips every ELF with `strip --strip-unneeded`.

### 2026-10-15 22:15:00
- **ci(packaging)**: Experimental aarch64 packaging workflow
  - New manual-only `.github/workflows/package-aarch64.yml` (`workflow_dispatch`). It builds the same target set as the release workflow (alpine/ubuntu/fedora/archlinux/void archives, AppImage, Flatpak, Nix) on `ubuntu-24.04-arm` runners and attaches the results - suffixed `-aarch64` so they never clobber the x86_64 assets - to the **same** versioned GitHub Release. Targets without an aarch64 image/build fail soft (`continue-on-error`).
  - `scripts/build_appimage.sh` now accepts `--arch=aarch64` (relocatable CPython + linuxdeploy/appimagetool from the aarch64 assets); `scripts/build_flatpak.sh` derives the output arch from `uname -m`.

### 2026-10-15 21:30:00
- **ci(packaging)**: AppImage & Flatpak release jobs + docs
  - `.github/workflows/package.yml` now builds a standalone x86_64 **AppImage** and a **Flatpak** bundle on every `v*` tag and ships them as release assets alongside the deb/rpm/tar.zst/nix packages. Both jobs are non-blocking (`continue-on-error`) so a bundle problem cannot block the rest of the release.
  - README + `installation.md` document the AppImage/Flatpak installs and the `clara` primary / `carla` backwards-compatible symlink naming.
  - Bumped Clara to **1.0.1**.

### 2026-10-15 20:30:00
- **chore(release)**: Clara 1.0.0 + portable packaging
  - Bumped the Clara application version to **1.0.0** (`CLARA_VERSION_STRING`, `aur/clara-bin/PKGBUILD`, `releases.json`).
  - New **Neo Candy** app icon (mixer glyph from the GPL-3.0 `neo-candy-icons` theme) replacing the legacy Carla bitmap/SVG set; rasterized to 16/32/48/128/256px.
  - New portable **AppImage** builder (`scripts/build_appimage.sh`) that bundles a relocatable CPython + PyQt6 (which ships its own Qt6) and the native libs for x86_64.
  - New **Flatpak** assets (`data/flatpak/…`) and builder (`scripts/build_flatpak.sh`).
  - New **git tag hook** (`scripts/git-hooks/pre-push` + `scripts/install-git-hooks.sh`): pushing a `v*` tag builds the AppImage and Flatpak locally into `dist/`.
  - `clara` is the primary binary/desktop name; `carla` remains as a backwards-compatible symlink.

### 2026-10-15 19:30:00
- **ui(settings)**: Sidebar typography, Nerd Font icons & label fixes
  - Sidebar tab buttons now render a **Nerd Font glyph + label** (General, Patchbay, Engine, OSC, File Paths, Plugin Paths, Wine, Experimental) in the detected Nerd Font instead of the cleared legacy bitmap icons; the sidebar font family now follows that font (with a clean sans fallback).
  - Replaced the remaining **legacy bitmap button icons** (project-folder open, and the Add / Change / Remove buttons on File Paths and Plugin Paths) with Nerd Font glyphs.
  - Fixed the **overly long descriptive label overlapping itself**: word-wrapped help/note labels now enable `heightForWidth` and top-left alignment so the layout reserves the full wrapped height.
  - Hid two **legacy options** that are no longer worth exposing: "Full canvas repaints (slower, …)" and "Load Carla backend in global namespace (NOT RECOMMENDED)".

### 2026-10-15 18:45:00
- **ui(patchbay)**: Search interaction restyle + settings widget polish
  - Search **results dropdown** selection/hover is now Catppuccin blue (`#89b4fa`) instead of the harsh orange, with a slim themed scrollbar and **no horizontal scrollbar** (results elide to the right and use uniform item sizes).
  - The on-canvas **search match highlight** was retinted from orange to sapphire (`#74c7ec` for matches, `#89b4fa` for the active row) to match the rest of the theme.
  - Settings dialog: added consistent theming for **combo boxes** (including their dropdown popup view), **spin boxes**, **line edits**, **check boxes** and all **scrollbars**, so the settings widgets no longer fall back to the default (ugly, horizontally-scrolling) platform style.

### 2026-10-15 18:15:00
- **ui(settings)**: Settings dialog cleanup
  - Removed the leftover decorative glyphs in the **upper-right corner of every settings tab** (the old `label_10` / `label_icon_engine_5` / `label_31` / `label_19` header icons were not matched by the previous hide list, so they lingered).
  - Removed the legacy inline **info / warning 16px icons** next to the descriptive text across Engine, OSC, File Paths, Plugin Paths, Wine and Experimental tabs; the text they annotated is kept.
  - Hid the deprecated **"Fancy eye-candy"** option (its toggle handler is disabled upstream).
  - Long help / note lines now **word-wrap** and render in a muted secondary color instead of clipping into a single unreadable line.

### 2026-10-15 17:30:00
- **feat(patchbay)**: Animated signal / event flow + search moved into the top toolbar
  - **Search box relocated**: the patchbay search field is no longer a standalone floater; it now lives inside the top context toolbar as a rounded text box that stays anchored to the bar (and follows it when dragged). The results popup still drops down beneath it.
  - **Signal flow animation**: new `patchcanvas/signalflow.py` animator drives a travelling pulse along every cable and lights up active nodes, using **real engine levels** (input/output peak values polled per plugin). Each pulse has a comet tail for a clear sense of direction; active nodes get both a tinted border and a body glow whose intensity tracks loudness. Levels are smoothed with fast attack / slow decay, and the pulse is now overlaid even on router/orthogonal cables that custom-draw themselves.
  - **External / PipeWire levels**: new `patchcanvas/pwlevels.py` samples the real level of external nodes (virtual **BUS** sinks, monitors, hardware I/O, external clients) using the same hidden peak-detect tap as pavucontrol (`PA_STREAM_PEAK_DETECT` via `libpulse`, pumped on the GUI thread). Activity is keyed by canvas **group id**, and any node with no sample (e.g. a playback stream like Spotify) falls back to a slightly attenuated level borrowed from the groups it is wired to, so a fully external chain still pulses as long as one Carla plugin sits anywhere on it. Cables light up from **either** endpoint.
  - **Clean patchbay**: the observer taps (ours and third-party ones like `pavucontrol` / `pwvucontrol`) are recognised by name and filtered out of the canvas, so they never appear as nodes or in port selectors. Per-node capture can be toggled from the right-click menu of the flow button (setting `Canvas/SignalFlowExternal`, default on).
  - **Quick switch**: a new toggle button (`heartbeat` glyph) in the left canvas palette enables/disables the animation, restored from the new `Canvas/SignalFlow` setting between sessions.
  - **Cleanup**: removed the bottom-right `?` patchbay shortcuts button (its help text lives on the left-palette `btnHelp` tooltip).

### 2026-10-15 15:45:00
- **feat(patchbay)**: Search selection now persists
  - `Ctrl+F` fuzzy search now *selects* the matching nodes in the scene (in addition to the highlight), so the result set stays selected after the search box closes via Enter, click or Esc.
  - The selection persists until the user interacts with the canvas - a canvas click/drag, or the select-all / invert-selection / deselect-all shortcuts, clears it (`_clearHighlights`).
  - Because the persisted selection emits `pluginSelected`, it also drives the mini-rack sync and the floating context toolbar, so you can search and then immediately arrange / act on the result set.

### 2026-10-15 15:00:00
- **feat(canvas)**: Graph introspection model
  - New `patchcanvas/graph_info.py`: a single JSON-serialisable view of the patchbay (`collect_graph`) - nodes (id, name, split, pos/size/rect, ports with mode/type), connections (out/in group+port+node index) and derived topology (edges, incoming, degree, connected components, longest-path layers). Foundation for the layout plugins and the future claractl / scripting layer.

### 2026-10-15 14:00:00
- **feat(canvas)**: Pattern-aware heuristic auto-arrange
  - New `heuristic` arrange algorithm (`patchcanvas/arrange_heuristic.py`), labelled "Heuristic (pattern-aware)", registered after `sugiyama` and selectable from the Arrange Tools menu.
  - It detects connection topology instead of applying a single rule: splits the graph into connected components (islands), then per component recognises exclusive pairs (side by side), fan-out (source beside a vertical stack of destinations), merges (sources aligned before the sink), fully connected cliques (compact grid), stars / hub-and-spoke (sources left, hub centre, sinks right), and plain chains (following signal flow). Anything unrecognised falls back to a layered pass with barycenter crossing reduction.
  - Deterministic (ties broken by node name), reuses `_nodeGraph`/`syncNodePositions`, honours snap/grid, and leaves island separation gaps so unrelated groups do not overlap.

### 2026-10-15 13:00:00
- **perf(canvas)**: Fix multi-second freeze when applying canvas settings (pressing OK) while a pure-Python router (`router`/`orthogonal`) is the active line style.
  - `slot_configureCarla` tears down and rebuilds the whole patchbay, so every cable re-routes once; at ~50-80 ms per long cable that meant several seconds of UI block.
  - `linealgo_ortho.py`: rewrote `_astar` to a flat array-indexed state space (`index = (cell*4)|dir`, list-based `dist`/`prev`, no per-node dict/tuple allocation) and capped grid resolution (`_MAX_CELLS=72`) so cable length no longer dictates A* work. ~50-80 ms/line → ~5-10 ms/line.
  - `linealgo_router.py`: same resolution cap (`_MAX_CELLS=72`) in `plan_waypoints`. ~11-15 ms/line → ~6-8 ms/line.
  - Net effect: a ~50-cable patch drops from ~3-4 s to a few hundred ms on settings apply.

### 2026-10-15 12:00:00
- **feat(canvas)**: Orthogonal router, Sugiyama arrange
  - New `orthogonal` line algorithm (`patchcanvas/linealgo_ortho.py`): self-contained Manhattan router, a direction-aware A* over an occupancy grid with a bend-aware cost (`length + bend_penalty·turns + soft cable-proximity cost`), node boxes as hard obstacles, neighbouring cables as soft obstacles, and rounded corners. Registered after `router`.
  - New `sugiyama` arrange algorithm (`patchcanvas/arrange_sugiyama.py`): classic layered layout - cycle breaking, longest-path layering, barycenter crossing reduction (down/up sweeps), even column placement. It appears in the Arrange Tools "Auto arrange" submenu automatically via the arrange registry.
  - Settings "Line style" combo picks up `orthogonal` with no extra code.

### 2026-10-15 11:15:00
- **refactor(canvas)**: Pluggable arrange algorithms, self-contained router plugin, router fix
  - New `patchcanvas/arrangealgos.py` registry mirroring `linealgos.py`: a `LayoutAlgorithm` interface (`arrange(nodes)`), `register_layout_algorithm`/`get_layout_algorithm`/`layout_algorithms`/`resolve_layout_algorithm`. Two built-ins: `classic` (the original signal-flow `autoArrange()`, still used by the context menus) and `flow` (the newer columnar, selection-aware layout; the default). `patchcanvas.autoArrangeNodes(nodes, algorithm=None)` now dispatches through the registry.
  - Arrange choice is selectable from the **Arrange Tools** popover ("Auto arrange" submenu) and persisted as `Canvas/ArrangeStyle` (`CARLA_KEY_CANVAS_ARRANGE_STYLE`, read in `carla_host`, stored on the Python-side `options_t.arrange_style`).
  - The `router` A* + flocking implementation moved out of the shared `patchcanvas/routing/` package into a single self-contained plugin module `patchcanvas/linealgo_router.py` (grid + A* + string-pulling + flocking + `RouterLineAlgorithm`). It still consumes only the public `LineContext` API; the `routing/` package was removed.
- **fix(canvas)**: Smart router no longer draws straight through node boxes
  - The A* search produced a correct detour, but flocking relaxation then pulled the waypoints back through the obstacle (the unit test was too lenient). Relaxation now (a) only applies the smoothing force when both neighbours can see each other (line-of-sight via the occupancy grid), (b) hard-projects any waypoint out of an inflated node box, and (c) validates the final polyline and falls back to the raw A* path if it ever tunnels. Added a real-`QGraphicsScene` integration test asserting no waypoint or segment enters an inflated node rect.

### 2026-10-15 10:30:00
- **feat(canvas)**: Obstacle-aware routing API (A* + flocking) and smart arrange/wire tools
  - New `patchcanvas/routing/` package: `grid.py` (scene-space occupancy grid), `astar.py` (A* search + string-pulling simplify), `flock.py` (force-based waypoint relaxation for cable spacing), and a single public entry point `plan_waypoints(ctx, ...)`. It consumes only a `LineContext` (endpoints, `nodes()`, `siblings()`), never patchcanvas internals.
  - Registered a new `router` line algorithm (`Smart router (A* + flocking)`): routes cables around node boxes and spaces them from sibling cables, falling back to bézier on failure. Not the default; `bezier` remains default.
  - New public canvas API (exported from `patchcanvas`): `autoArrangeNodes()`, `autoWire()`, `autoArrangeAndWire()`, `autoRepelNodes()`. Arrange uses signal-flow column layering; wire chains nodes in topological order using compatible free ports and requests connections through the normal canvas callback; repel falls back to the whole canvas when nothing is selected.
  - Canvas context toolbar now exposes a grouped **Arrange Tools** popover (auto arrange / auto wire / arrange + wire / auto repel), replacing the separate arrange/repel buttons so the bar stays uncluttered. Wire/both are disabled with no selection.

### 2026-10-15 09:05:00
- **refactor(canvas)**: Retire adaptive, default to bézier
  - `adaptive` hybrid dispatcher removed from the registry; `bezier` is the default again (`CARLA_DEFAULT_CANVAS_LINE_STYLE`, `patchcanvas.options.line_style`). A future A* + flocking router will replace it.

### 2026-10-15 08:40:00
- **fix(canvas)**: Line styles collapsed to straight; tune adaptive hybrid
  - Every non-`bezier` style rendered as a straight line: the settings dialog writes the legacy `Canvas/UseBezierLines` flag as `False` for any non-bezier pick, and `resolve_line_algorithm()` treated that as "force straight". The `line_style` string is now authoritative and the legacy boolean is ignored (`linealgos.py`, `patchcanvas/__init__.py`).

### 2026-10-15 08:20:00
- **feat(canvas)**: New cable shapes + adaptive hybrid routing
  - Added a registered `circuit` line algorithm (H/V trace with rounded corners and sibling-based lane offsets).
  - Renderer flags renamed/clarified: `dynamic` (re-route all cables on node moves; `tracks_others` kept as a read alias) and `selection_sensitive` (re-route on selection change, coalesced per event-loop tick). Dynamic re-routes are coalesced in `CanvasBox.repaintLines` to at most once per event-loop tick.
  - New geometry helper `rounded_polyline` used by the circuit shape.

### 2026-10-15 07:05:00
- **refactor(canvas)**: Pluggable line-algorithm registry for patchbay cables
  - Connection shape logic was spread across `if/elif` chains in `canvasline.py`, the drag previews (`canvaslinemov.py` / `canvasbezierlinemov.py`), and the settings combo. New `patchcanvas/linealgos.py` introduces a `LineAlgorithm` interface (`build_path` / `build_drag_path`, plus `line_type`, `mov_line_type`, `cap_style`) with a registry (`register_line_algorithm`, `get_line_algorithm`, `line_algorithms`).
  - Algorithms receive a `LineContext` (endpoints + `direction` + the ports/connection/`canvas`), not bare points, so complex renderers are possible: `ctx.siblings()` yields every other cable for coupling/bundling, `ctx.nodes()` yields `(group_id, QRectF)` for node-avoidance routing, and `paint(painter, ctx, path)` plus `params()` are optional hooks. Setting `dynamic = True` makes the canvas re-route all cables on node moves so bundles stay in sync.
  - `BezierLineAlgorithm`, `StraightLineAlgorithm`, and `SteppedLineAlgorithm` are registered out of the box; adding a new shape is one class + `@register_line_algorithm` with zero branching changes elsewhere.
  - Drag previews are now a single registry-driven `CanvasLineMov`, so `stepped` gets a live preview too (previously only bezier/straight). Old `CanvasBezierLine` / `CanvasBezierLineMov` names remain as backward-compatible aliases.
  - The settings "Line style" combo is populated from the registry instead of a hardcoded list (`carla_settings.py`).

### 2026-10-15 06:11:30
- **fix(ui)**: Restore `Qt.Key_Backspace` (Qt6 compat)
  - `qt_compat` aliased most `Qt.Key_*` names to their Qt6 `Qt.Key.*` enum for bindings compatibility, but `Key_Backspace` was missing, so deleting a plugin with Backspace crashed with `AttributeError: type object 'Qt' has no attribute 'Key_Backspace'` (`carla_skin.py:1656`). Added the alias.

### 2026-10-15 06:02:45
- **chore(ui)**: Log the active patchbay viewport at startup
  - The canvas startup now logs whether the patchbay is `OpenGL` or `Software raster`, the viewport update mode, and the `Canvas/UseOpenGL` setting, so it is obvious from the terminal whether GPU rendering is actually active.

### 2026-10-15 05:41:20
- **perf(ui)**: Smoother canvas panning and further drag/repaint savings
  - Box drop-shadows are now also skipped while panning the canvas (not just during a node drag), so the strips exposed by scrolling are cheap to redraw.
  - The canvas view no longer adjusts update rects for antialiasing (`DontAdjustForAntialiasing`) and the viewport is marked opaque (`WA_OpaquePaintEvent`), keeping repaints smaller and skipping Qt's background erase.
  - The grid dots are now drawn in a single `drawPoints` call with a round-capped pen instead of thousands of individual `drawRect` calls.
  - The minimap no longer draws the canvas grid while rendering the scene to its cache (invisible at that scale), making minimap refreshes noticeably cheaper.

### 2026-10-15 05:26:10
- **fix(ui)**: Ask about Ctrl+C in the terminal, not with a GUI dialog
  - Pressing Ctrl+C now prints a plain prompt (`[K]ill` / `[T]ray + detach`) in the terminal where the key was pressed, instead of popping a `QMessageBox`.
  - Fixed the previous implementation crashing: `QMessageBox.YesRole`/`NoRole` don't exist on the class in this Qt build, and the failure fallback called `logger.warning()` with a single argument (the logger requires a tag plus message), so the prompt died with an `AttributeError`/`TypeError`.
  - The prompt is shown whenever Carla runs from a TTY; the tray/detach option is only offered when a system tray is available.

### 2026-10-15 05:24:03
- **perf(ui)**: Smoother patchbay node dragging
  - Box drop-shadows no longer recompute their blur on every drag frame: while a box is being dragged the shadow is skipped (the box is painted directly) and restored on release, removing the main source of drag lag.
  - Position changes are no longer written to settings and pushed to the engine on every drag frame; they are flushed once when the drag ends, avoiding a synchronous settings write plus engine callback per frame.
  - The grid background is now cached by the canvas view (`CacheBackground`) and painter state is not saved (`DontSavePainterState`), so the dotted grid is not repainted for every dot on each drag/pan frame.

### 2026-10-15 05:01:41
- **feat(ui)**: Prompt on Ctrl+C (SIGINT) instead of quitting immediately
  - SIGINT is now routed separately from SIGTERM: SIGTERM still closes immediately (needed by session managers/systemd), while SIGINT pops a dialog.
  - Dialog offers "Kill Carla" (default, `Y`/Enter) or "Tray + Detach" (default-less `N`), the latter minimising to the system tray and detaching from the controlling terminal (`setsid`, `SIGHUP` ignored, stdio redirected) so the app survives the terminal closing.
  - Only prompts when launched from a TTY with a system tray available; otherwise it closes as before.

### 2026-10-15 04:52:16
- **feat(ui)**: Edge auto-scroll when dragging the minimap view scope
  - Left-dragging the view scope to (or beyond) a minimap edge now continuously pans the minimap and the main patchbay canvas, ramping speed with how far past the edge the cursor is.
  - Auto-scroll stops automatically when the cursor returns inside the map or the view reaches the edge of the node bounds.

### 2026-10-15 04:46:41
- **fix(ui)**: Minimap phantom node, bottom-scope clamping and collapse button
  - Phantom node: hidden / not-yet-portable group boxes (created at `(0,0)`) were being outlined because `scene.items()` includes invisible items; the minimap and scene-rect expansion now skip invisible items.
  - View scope could not be panned to the bottom until manually scrolling: scene/view rect expansion only ran once at setup (before plugins loaded). It now also runs from `updateMiniCanvasLater()` (client add/remove/rename) and updates both the scene and the view scene rect.
  - Collapse button did nothing: `QToolButton.clicked` passes a bool check-state into `toggleCollapsed(collapsed)`, making every click evaluate as "no change"; the connection is now wrapped so it toggles.

### 2026-10-15 04:31:06
- **feat(ui)**: Blender-style minimap overlay, discoverability and persistence
  - Replaced the top `✕` bar with a compact grip (drag to move) and a corner collapse tab; hide/expand and zoom-reset moved into a right-click context menu.
  - Added a zoom-level badge (`FIT` / percentage) and an on-map control hint so wheel-zoom, middle-drag pan and double-click reset are discoverable.
  - Minimap now expands the patchbay scene rect to the union of node bounds (+margin) so the bottom of the canvas can actually be panned to at startup.
  - Reduced early misplacement: placement now waits for valid geometry and re-clamps via deferred repositioning.
  - Persisted `Minimap/X`, `Minimap/Y`, `Minimap/Zoom`, `Minimap/Collapsed` and `Minimap/Visible` in `QSafeSettings` (app-wide), restored at startup and saved on drag/collapse/zoom/hide and on settings save.

### 2026-10-15 04:14:49
- **fix(ui)**: Render modern minimap from the live scene with contrast-corrected node outlines
  - Replaced the hand-drawn bounding-box fill with a real `QGraphicsScene` render, matching the classic minimap so node bodies, headers, ports and cables keep their true appearance.
  - Outlined every node using its own custom color (theme color when uncolored), passing it through a WCAG luminance/contrast check that lightens or darkens the color against the background so all nodes stay visible.
  - Added minimap-internal zoom (mouse wheel, cursor-anchored), middle-drag panning, and double-click reset so large patches stay readable.

### 2026-10-15 03:09:23
- **feat(ui)**: Float minimap into hideable patchbay viewport overlay
  - Reparented `miniCanvasPreview` out of the side dock into a rounded overlay anchored at the bottom-right of the patchbay viewport.
  - Placement is mode-aware: Modern UI mode uses the floating overlay, while Classic mode restores the original sidebar minimap.
  - Added hide (`✕`) and restore (`Map`) controls so the minimap can be dismissed and brought back on demand.
  - Kept existing canvas navigation and theming behavior intact while repositioning on viewport resize.

### 2026-10-15 00:00:00
- **feat(ui)**: Add "Minimize to system tray" option
  - Added `Main/MinimizeToTray` setting (default off) in Settings with load/save/reset.
  - Main window minimizes to a system tray icon with Show/Quit menu and restores on activation.

## [0.1.5] - 2026-10-13

### 2026-10-13 23:05:00
- **fix(ci)**: Purge ccache from packaging pipeline and fix canvas icon warning
  - Completely removed `ccache` from packaging workflow jobs to prevent caching older Qt6 symbol ABIs (`_ZN8QVariantC1EO7QString`).
  - Switched canvas side-by-side view icon fallback cleanly to `view-refresh` to prevent `Cannot open file ':/16x16/view-split-top-bottom.svgz'` Qt warnings.
  - Bumped version to `0.1.5`.

## [0.1.4] - 2026-10-13

### 2026-10-13 22:10:00
- **fix(packaging)**: Fix Arch Linux Qt6 ABI crash and invalidate stale CI cache
  - Resolved `undefined symbol: _ZN8QVariantC1EO7QString` crash on Arch Linux by scoping CI `ccache` cache key to `ccache-v2-` and ensuring clean build targets.
  - Standardized application window title, logs dialog (`Clara Logs`), and About dialog window title to **Clara**.
  - Fixed missing SVG icon warning for canvas side-by-side view toggle.
  - Bumped `CLARA_VERSION_STRING`, `releases.json`, and AUR `clara-bin` PKGBUILD to `0.1.4`.

### 2026-10-13 21:42:00
- **feat(ui)**: Add timed support banner & purge all emoji from banners and dialogs
  - Added `SupportNotificationBanner` scheduled via a 10-minute timer (`QTimer.singleShot(600000)`) with sponsor links for maintainers (`acropolis914` and `falkTX` from `.github/FUNDING.yml`: GitHub Sponsors, Patreon, Liberapay, PayPal).
  - Added "Support Clara..." menu action in Help menu and hidden CLI flag `--show-support-banner` to display banner immediately for verification.
  - Provided snooze actions: "Hide for 1 Month" (persisted for 30 days via `QSettings`) and "Never Show Again".
  - Cleaned all banner and dialog buttons/headers to be strictly emoji-free.

### 2026-10-13 21:33:00
- **feat(updates)**: Add interactive terminal updater and Open Releases Page action
  - Created embedded `scripts/clara_self_updater.sh` featuring automatic distro family detection (`/etc/os-release`), fallback interactive picker, ANSI styling, and `pkexec`/`sudo` elevation.
  - Replaced banner download button with **⚡ Update Now** (auto-detects and launches terminal emulator) and **🌐 Releases Page**.
  - Configured `Makefile` to install `clara_self_updater.sh` into `$(DATADIR)/carla/scripts/` across all distribution packages.
  - Terminates updates with `Installed. Press enter to exit, please restart Clara`.

### 2026-10-13 21:19:00
- **fix(updates)**: Verify compiled distro binaries exist before prompting update
  - Added GitHub Releases API check in `UpdateCheckThread` to explicitly verify that compiled packages (`.deb`, `.rpm`, `.tar.zst`) have finished uploading, ignoring default auto-generated source zips.
  - In manual checks while packages are building, notifies the user that the release is currently compiling.


### 2026-10-13 21:12:00

- **ci(packaging)**: Standardize release artifact filenames to use release tag version
  - Replaced commit SHA hashes (`${{ github.sha }}`) with release tag versions (`${VERSION}`) across all distro packages (`clara-archlinux-${VERSION}.tar.zst`, `clara-ubuntu-${VERSION}.deb`, etc.).
  - Resolves broken download URLs in AUR `clara-bin` PKGBUILD.

### 2026-10-13 21:07:00

- **docs(sponsors)**: Prioritize acropolis914 GitHub Sponsors in funding & README
  - Added direct GitHub Sponsors badge (`https://github.com/sponsors/acropolis914`) to the `README.md` header.
  - Linked GitHub Sponsors alongside PayPal in the top announcement alert banner.

### 2026-10-13 20:46:00

- **feat(updates)**: Separate Clara and Carla versioning & add manual update checks
  - Introduced `CLARA_VERSION_STRING` ("0.1.2") in `carla_shared.py` to prevent version comparison conflicts with upstream Carla `2.6.0-alpha1`.
  - Added "Check for Updates..." to the Help menu and toolbar menu with immediate feedback dialogs (up-to-date confirmation and error diagnostics).
  - Enhanced update notification banner to slide into the top layout on update detection and display changelog modal dialog on critical or suggested releases.
  - Updated About dialog to distinguish Clara application version from underlying Carla core engine version and added a direct link to GitHub Releases.

### 2026-10-13 20:40:00
- **docs(funding)**: Add upstream creator falkTX funding channels to FUNDING.yml
  - Included falkTX's GitHub Sponsors, Patreon, Liberapay, and PayPal alongside Clara maintainer sponsorship links.

### 2026-10-13 20:16:00

- **feat(ui)**: Add animated loading dialog and modernize About screen
  - Introduced modal `ProjectLoadingDialog` with an indeterminate marquee progress bar and real-time detailed status text pumped via engine event callbacks for project restoration.
  - Revamped About screen: removed legacy bitmap logos and outdated fonts, attributed project maintenance to `acropolis914`, and added direct links to the Clara repository and GitHub Sponsor page.

### 2026-10-13 20:03:00
- **refactor(patchbay)**: Make camera autofocus pan-only and faster
  - Removed zoom scaling in `animateFocusOn` to provide pure, crisp pan travel and shortened duration to 260ms for snappy response.

### 2026-10-13 20:00:00
- **refactor(ui)**: Smooth patchbay camera animation and restyle floating add button
  - Replaced matrix reset scaling with incremental scaling in `animateFocusOn` to eliminate camera anchor jitter during flight.
  - Redesigned floating `+ Add Plugin` button to use cohesive dark glassmorphism palette matching Carla's Catppuccin theme.

### 2026-10-13 19:58:00
- **fix(rack)**: Resolve context menu remove and move action dispatch
  - Fixed erroneous `elif actMoveUp:` check that swallowed subsequent menu actions, restoring the context menu `Remove` confirmation and execution.

### 2026-10-13 19:56:00
- **fix(rack)**: Ensure delete confirmation dialog triggers reliably and add floating add button
  - Added keypress interception for `Delete`/`Backspace` directly on rack slot widgets with parent window anchoring for the confirmation dialog.
  - Added a floating `＋ Add Plugin` action button anchored to the bottom-right corner of the rack list view.

### 2026-10-13 19:51:00
- **feat(patchbay)**: Animate node autofocus with cubic bezier easing and zoom dip
  - Implemented `animateFocusOn()` in `DraggableGraphicsView` featuring `QEasingCurve.InOutCubic` camera travel and a subtle mid-flight zoom-out/zoom-in parabolic arc on rack item selection and patchbay search.

### 2026-10-13 19:44:00
- **feat(patchbay)**: Add configurable minimum node width
  - Introduced `Canvas/NodeMinWidth` setting with slider control in the Canvas settings tab, dynamic options propagation, and CanvasBox width enforcement (default 160px).

### 2026-10-13 19:34:00
- **feat(rack)**: Enforce uniform fixed grid dimensions for parameter dials in minimal skin
  - Configured `setFixedSize(68, 54)` and aligned flow layout spacing on `w_knobs_left` so rack dials arrange into a uniform grid with unclipped labels.

### 2026-10-13 19:27:00
- **fix(rack)**: Ensure header buttons, badge, and title anchor to the far left
  - Cleared fixed template spacers and inserted action buttons (index 0), type badge (index 1), and title (index 2) at the start of `layout_top`.

### 2026-10-13 19:24:00
- **feat(patchbay)**: Trigger zoom to fit after applying deferred hidden ports on load
  - Added `canvas.scene.zoom_fit()` after hiding unconnected ports on session loading to frame all graph nodes neatly.

### 2026-10-13 19:22:00
- **fix(ui)**: Add `Qt.TextElideMode` compatibility aliases in `qt_compat.py`
  - Added `Qt.ElideRight`, `Qt.ElideLeft`, and `Qt.ElideMiddle` aliases for PyQt6, resolving AttributeError during dynamic title elision in `resizeEvent`.

### 2026-10-13 19:20:00
- **fix(rack)**: Prevent access to replaced layout in `PluginSlot_Minimal`
  - Replaced stale reference to `self.ui.horizontalLayout_3` with safe check on `self.w_knobs_left.layout()`, resolving RuntimeError on plugin instantiation.

### 2026-10-13 19:19:00
- **fix(ui)**: Export and import `QSpacerItem` across Qt5/Qt6 compatibility layer
  - Added `QSpacerItem` to `qt_compat.py` QtWidgets exports and imported it into `carla_skin.py`, fixing plugin slot initialization failure.

### 2026-10-13 19:13:00
- **fix(frontend)**: Resolve About Dialog `unwrapinstance` crash under PyQt6
  - Added support for `PyQt6.sip.unwrapinstance` in `carla_frontend.py` to prevent TypeError on `HostWindow`.
- **feat(rack)**: Dynamic title elision on resize and distributed grid width for knobs
  - Switched title truncation to responsive font-metrics elision that only truncates when space is constrained.
  - Standardized dial columns to a distributed 68px grid width to maintain aligned parameter rows without label clipping.

### 2026-10-13 19:11:00
- **docs(readme)**: Add student developer donation note to top banner
  - Added personal student funding note with direct PayPal link to README announcement banner.

### 2026-10-13 18:43:00

- **docs(funding)**: Add GitHub FUNDING.yml configuration
  - Created `.github/FUNDING.yml` to display repository sponsorship button and funding links.

### 2026-10-13 18:42:00

- **docs(readme)**: Clarify AI policy and make alpha announcement imperative
  - Rephrased top callout banner in `README.md` to be directly imperative about bug reporting and contributing.
  - Removed "encouraged" phrasing from AI development policy in `README.md` and `CONTRIBUTING.md`, designating AI tools as strictly permitted under full contributor review.

### 2026-10-13 18:41:00

- **feat(rack)**: Restructure header into flex layout and modernize preset selector
  - Reordered header into `<buttons> <type badge> <title> <auto-expanding spacer> <right modules>` with tightened spacing.
  - Limited title length to 20 characters with ellipsis while preserving the full name in tooltip.
  - Modernized `cb_presets` with a translucent pill surface, subtle border, custom drop indicator, and themed popup menu.

### 2026-10-13 18:35:00
- **fix(ui)**: Resolve missing `QRadialGradient` import in `LEDButton`
  - Cleaned up unused gradient import in `widgets/ledbutton.py` to restore clean frontend launch.

### 2026-10-13 18:34:00
- **feat(ui)**: Reskin 2x2 LED status indicators for modernized header slice
  - Added clean geometric vector rendering with vivid glow and distinct dark states in `LEDButton`, activated exclusively when Modernized Header Slice is enabled.

### 2026-10-13 18:28:00
- **fix(ui)**: Register Qt resource bundle into PyQt6 runtime
  - Fixed missing button pixmaps and icons across classic and modern rack skins by registering `resources_rc` data into `PyQt6.QtCore.qRegisterResourceData`.

### 2026-10-13 18:21:00
- **feat(rack)**: Calibrate smooth scroll easing rate for gentle visual glide
  - Softened easing rate from 28% to 10% per frame and added a 24px/tick velocity limit in `RackListWidget`.

### 2026-10-13 18:06:00
- **feat(rack)**: Smooth scroll rack item into view when clicking corresponding node in patchbay
  - Added `scrollToItemSmooth` to `RackListWidget` with viewport centering and easing interpolation.
  - Linked `slot_canvasPluginSelected` to call `scrollToItemSmooth`, smoothly bringing the plugin slot into focus.

### 2026-10-13 18:03:00
- **fix(patchbay)**: Fix connected port detection when hiding unused ports
  - `CanvasBox.updatePositions` now inspects both global `canvas.connection_list` and node-local `m_connection_lines` to ensure all active wires (including split and re-routed node ports) are recognized as connected.

### 2026-10-13 18:00:00
- **fix(patchbay)**: Resolve cable disconnect misalignment with hidden unconnected ports and reorder Settings menu
  - Connected and re-connected ports now trigger immediate box recalculation (`updatePositions`) on nodes with hidden unconnected ports active, and deferred hiding re-syncs all cable geometries after backend connections finalize.
  - Reorganized Settings menu with panels/toggles grouped first, followed by standalone logs, and `Configure Carla...` placed cleanly at the bottom.

### 2026-10-13 17:41:00
- **feat(rack)**: Implement smooth pixel-based scrolling in Rack list
  - Configured `RackListWidget` with pixel scrolling mode (`ScrollPerPixel`) instead of discrete item stepping.
  - Implemented an animated easing timer (`_on_smooth_scroll_tick`) with fractional interpolation for fluid mouse-wheel navigation through plugin strips.

### 2026-10-13 17:35:00
- **fix(ui)**: Unified flush look for Modern Patchbay+Rack workspace and functional Statusbar toggle
  - Removed container borders, frame shapes, and pane outlines between Rack and Patchbay in Modern side-by-side mode for a continuous flush aesthetic matching the canvas theme.
  - Implemented `Show Statusbar` toggle in Settings and menus, connecting directly to the bottom engine statusbar (`tw_statusbar`) displaying buffer size, sample rate, and DSP load.

### 2026-10-13 17:28:00
- **feat(ui)**: Modern / Classic UI mode switch, unified workspace, and native error loading dialog
  - Refactored `ProjectLoadSummaryDialog` to use system Qt theme styling and native controls without hardcoded color themes.
  - Introduced `Modern UI Mode` toggle in Settings (defaulting to enabled), unbarring Patchbay + Rack into a unified single workspace without tab bar clutter.
  - Decoupled Logs tab into a standalone window via `Show Logs Window` action when in Modern unified view mode, while preserving Classic multi-tab view mode on toggle.

### 2026-10-13 17:11:00
- **feat(ui)**: Default to side-by-side view, no toolbar, and floating menu button when menubar is hidden
  - Added hamburger menu button directly on the floating patchbay toolbar overlay so main menus remain accessible when top menubar and toolbar are both hidden.
  - Set application defaults in `loadSettings`: side-by-side view enabled by default, main toolbar hidden by default, and menubar hidden by default.
  - Safeguarded `gCarla.gui` access in `canvasCallback` during application teardown.

### 2026-10-13 17:10:00
- **tools(aur)**: Add local release and AUR publishing helper script
  - Created `scripts/release_and_push_aur.sh` to update `releases.json`, bump `aur/clara-bin/PKGBUILD`, push the version tag to GitHub, generate `.SRCINFO`, and push directly to `ssh://aur@aur.archlinux.org/clara-bin.git`.

### 2026-10-13 17:05:00

- **packaging(aur)**: Add clara-bin PKGBUILD and automated version bump step
  - Created `aur/clara-bin/PKGBUILD` packaging the pre-compiled GitHub release archive for Arch Linux users without build overhead.
  - Added automated GitHub Actions step in `.github/workflows/package.yml` to bump `pkgver` in `aur/clara-bin/PKGBUILD` and push to main upon tag releases.
  - Updated `installation.md` and `README.md` to document `clara-bin` and `clara-git` options.

### 2026-10-13 16:57:00

- **fix(backend)**: Add system library fallbacks for carla-bridge-native
  - Added fallback search in `/usr/lib/carla` and `/usr/lib64/carla` when `carla-bridge-native` is not present in the local `bin/` folder.
  - Prevents fatal crashes when in-process JUCE plugins (`KV-Element`) require bridge isolation.

### 2026-10-13 16:47:00
- **fix(frontend)**: Resolve missing LEVEL_NAMES, QLabel, and os imports in ProjectLoadSummaryDialog
  - Imported `LEVEL_NAMES` in `carla_host.py` from `carla_logger`.
  - Added missing `QLabel`, `QPushButton`, `QTextEdit`, `QHBoxLayout`, and `os` imports in `carla_widgets.py`.

### 2026-10-13 16:43:00
- **feat(project)**: Add post-load summary dialog with skipped plugins and one-click log copy
  - Wrapped `load_project()` in try-catch and error callback monitoring to prevent aborted sessions when individual plugins fail.
  - Implemented `ProjectLoadSummaryDialog` in `carla_widgets.py` showing failed/skipped items, raw diagnostic logs, and a "Copy Log to Clipboard" button.

### 2026-10-13 16:40:00
- **docs(issues)**: Add GitHub issue template config.yml
  - Configured `.github/ISSUE_TEMPLATE/config.yml` disabling unstructured blank issues.
  - Linked GitHub Discussions and upstream documentation directly in the issue chooser.

### 2026-10-13 16:24:00

- **fix(patchcanvas)**: Implement and export centerGraphInCanvas for project canvas positioning
  - Implemented `centerGraphInCanvas()` in `source/frontend/patchcanvas/patchcanvas.py` filtering out None widgets and centering graph nodes when loading projects.
  - Exported `centerGraphInCanvas` in `source/frontend/patchcanvas/__init__.py`.

### 2026-10-13 08:04:00
- **fix(frontend)**: Fix _on_update_available method placement inside HostWindow class
  - Relocated `_on_update_available` callback inside the `HostWindow` class scope so Qt signal connection resolves correctly.

### 2026-10-13 08:00:00
- **fix(build)**: Prioritize Qt6 over Qt5 when pyuic6 is present
  - Swapped Qt5/Qt6 detection ordering in `source/Makefile.deps.mk` so `pyuic6` is selected when building with `DEFAULT_QT=6`, resolving PyQt5/PyQt6 widget mismatch exceptions.

### 2026-10-13 07:52:00
- **fix(frontend)**: Export QThread, QTextEdit, and QSettings in qt_compat and fix version import
  - Exported `QThread`, `QTextEdit`, and `QSettings` across Qt5 and Qt6 sections of `qt_compat.py`.
  - Updated `update_checker.py` to import `CARLA_VERSION_STRING` from `carla_shared`.
  - Ensured `PKGBUILD` passes `DEFAULT_QT=6` during install stage.

### 2026-10-13 15:39:00
- **ci(workflow)**: Restrict multi-distro packaging workflow strictly to tag pushes
  - Removed standard `main` branch push and weekly cron triggers from `.github/workflows/package.yml`.
  - Configured packaging pipeline to trigger exclusively on version tags (`v*`) and manual `workflow_dispatch`.

### 2026-10-13 15:35:00

- **docs(suggestions)**: Add SUGGESTIONS.md and feature request issue template
  - Added `SUGGESTIONS.md` outlining GitHub Discussions channels and proposal guidelines.
  - Added `.github/ISSUE_TEMPLATE/feature_request.md` for structured feature requests.
  - Linked Ideas & Suggestions into the primary `README.md` navigation bar.

### 2026-10-13 07:34:00

- **feat(desktop)**: Add clara.desktop entry and clara binary symlink
  - Added `data/desktop/clara.desktop` system application launcher.
  - Added `clara` binary symlink in `` pointing to `carla` for direct command-line launch.

### 2026-10-13 15:33:00
- **docs(readme)**: Modernize README, add CONTRIBUTING guide, and GitHub issue template
  - Removed raw emoji clutter from README.md in favor of Catppuccin badges and clean typography.
  - Added early-alpha contributor and bug-reporting callout banner.
  - Added `CONTRIBUTING.md` detailing setup, Conventional Commits, and explicit AI disclosure requirements.
  - Added `.github/ISSUE_TEMPLATE/bug_report.md` for structured bug reporting.

### 2026-10-13 07:30:00

- **feat(updates)**: Add non-blocking background update checker and dismissable top notification banner
  - Added structured `releases.json` with urgency levels (`suggested`, `minor`, `critical`), changelogs, and installation instructions.
  - Implemented `UpdateCheckThread` and `UpdateNotificationBanner` in `update_checker.py` with non-blocking 3s timeout.
  - Added "Hide" and "Skip Version" actions with confirmation dialog and `QSettings` persistence.
  - Updated `AGENTS.md` guidelines to mandate updating `releases.json` alongside `CHANGELOG.md`.
  - Added `clara-bin` AUR packaging task to `TODO.md`.

### 2026-10-13 06:58:00
- **fix(fedora)**: Disable RPM debuginfo package generation
  - Added `%global debug_package %{nil}` to `clara.spec` to prevent rpmbuild from failing on empty debugsource lists.

### 2026-10-13 06:49:00
- **fix(fedora)**: Package all installed files under /usr/* in RPM spec
  - Simplified `%files` in `clara.spec` to include `/usr/*`, resolving missing lib64 path errors and invalid `%optional` spec macro directives.

### 2026-10-13 06:42:00
- **fix(fedora)**: Package pre-compiled binaries directly into RPM without redundant recompilation
  - Updated `clara.spec` and packaging step to use `rpmbuild -bb` on the already-compiled tree, eliminating redundant build failures and slashing package creation time to seconds.

### 2026-10-13 06:18:00
- **fix(nix)**: Fix SDL2 casing in Nix derivation and strictly verify build result
  - Corrected `sdl2` to `SDL2` in `nix/default.nix` to resolve nixpkgs evaluation error.
  - Required valid `./result` derivation path before creating Nix tarball artifact.

### 2026-10-13 06:15:00
- **fix(fedora)**: Correct SMP make flags syntax in RPM spec
  - Fixed duplicate `-j` flag by using standard `%{?_smp_mflags}` macro in `clara.spec` to avoid make argument errors.

### 2026-10-13 06:09:00
- **ci(matrix)**: Enable fail-fast to immediately abort entire build on any distro failure
  - Changed `fail-fast: true` on the packaging matrix.

### 2026-10-13 06:08:00
- **fix(fedora)**: Replace %make_build macro with direct make invocation
  - Switched from Fedora `%make_build` macro to `make -j%{_smp_mflags} DEFAULT_QT=6` in `clara.spec` to prevent strict Red Hat compiler hardening flags from breaking bundled C dependencies (lilv/serd).

### 2026-10-13 06:00:00
- **perf(ci)**: Accelerate CI compilation with parallel make and ccache caching
  - Enabled `make -j$(nproc)` to utilize all 4 runner CPU cores concurrently.
  - Configured `actions/cache@v4` with `ccache` across distros to reuse compiled object files across builds.

### 2026-10-13 05:56:00
- **fix(fedora)**: Add python3-devel to build dependencies
  - Added missing `python3-devel` package to Fedora DNF installation to satisfy RPM build dependencies.

### 2026-10-13 05:49:00
- **fix(rpm)**: Fix RPM spec release tag token syntax and align source archive name
  - Changed `Release` in `clara.spec` to standard `1%{?dist}` to avoid unexpanded GitHub Actions expression syntax errors in rpmbuild.
  - Aligned Fedora source archive filename with `clara-source.tar.gz`.
  - Updated README to point download links directly to release tags.

### 2026-10-13 05:47:00
- **ci(release)**: Add automated GitHub Releases on tag push with changelog extraction
  - Configured `release` job triggered exclusively on `v*` tag pushes to attach all distro package artifacts.
  - Automatically extracts latest changelog notes from `CHANGELOG.md` into the GitHub Release body.
  - Added installation & download table in `README.md` covering all supported distributions.

### 2026-10-13 05:41:00
- **ci(void)**: Isolate void-musl build to host docker container
  - Migrated `void-musl` build to a host runner job using `docker run` to prevent musl dynamic-linking incompatibilities with GitHub Actions Node.js runner.

### 2026-10-13 05:36:00
- **fix(ci)**: Fix POSIX sh pipefail compatibility and container spec path
  - Removed unsupported `set -o pipefail` from Alpine/Void `/bin/sh` build scripts.
  - Corrected Fedora RPM spec lookup to use relative `.github/workflows/specs/clara.spec` inside the container workspace.

### 2026-10-13 05:32:00
- **feat(nix)**: Add Nix derivation, devShell, and Flake configuration
  - Added `nix/default.nix` for packaging Clara using `stdenv.mkDerivation` and Qt6 build hooks.
  - Added `nix/shell.nix` for developer environment and debugging tooling.
  - Added root `flake.nix` with default package, app runner, and devShell outputs.
  - Updated CI Nix workflow to invoke `nix build` with Flakes enabled.

### 2026-10-13 05:25:00
- **ci(packaging)**: Add void-musl build, fix deb/rpm/arch artifact packaging, and isolate Nix to host runner
  - Split Void Linux packaging into `void-glibc` and `void-musl` with musl-fts support.
  - Isolated Nix into a dedicated host runner job using `DeterminateSystems/nix-installer-action` to resolve container Node execution failures.
  - Corrected Debian packaging via `dpkg-deb` and Fedora RPM spec install rules using `make install`.
  - Added Arch Linux zstd tarball packaging target.

### 2026-10-13 05:03:00
- **fix(ui)**: Fix Ctrl+M menubar double-press requirement and infinite canvas panning on right edge
  - Moved `act_settings_show_menubar` and hamburger button setup before `loadSettings(True)` so that restored menubar visibility state immediately syncs with the action state, eliminating the initial double-press bug.
  - Enhanced canvas empty-area hit testing to check `topLevelItem()` to avoid false negatives on child elements.
  - Implemented dynamic scene boundary expansion during panning in `DraggableGraphicsView` so panning smoothly continues across infinite canvas coordinates without hitting scrollbar clamp limits on the right or bottom.
- **feat(settings)**: Refine settings sidebar typography, dimensions, and outline removal
  - Compacted tab row heights to 32px and trimmed sidebar width to 136px.
  - Replaced monospace font with modern system sans-serif font stack (`-apple-system`, `Inter`, `Roboto`, `Segoe UI`).
  - Removed table item outlines and softened border separators with translucent Catppuccin surface styling.
  - Polished button and group box outlines with clean rounded corners and unified accent highlights.

### 2026-10-13 04:10:00
- **fix(settings)**: Import `QSize` and `QIcon` from `qt_compat`
  - Fixed `NameError: name 'QSize' is not defined` when initializing settings sidebar icon size.

### 2026-10-13 04:09:00
- **fix(settings)**: Import `gCarla` and modernize settings tab layout and headers
  - Fixed `NameError: name 'gCarla' is not defined` during live updates (`_on_live_rack_spacing`, `_on_live_rack_padding`, `_on_live_rack_min_width`, `_on_live_statusbar_toggle`).
  - Removed outdated tab icons and replaced with modern typography and clean tab labels in `lw_page`.
  - Hid legacy page header icons (`label_icon_*`) across all settings dialog tabs.
- **fix(settings)**: Correct parent widget for `group_rack_geometry` in `CarlaSettingsW`
  - Fixed `AttributeError: 'Ui_CarlaSettingsW' object has no attribute 'tab_main'` by referencing `page_main` and `verticalLayout_5`.

### 2026-10-13 03:56:00
- **feat(settings)**: Overhaul Settings UI with live tweakables and modern Catppuccin styling
  - Exposed live interactive sliders for rack item vertical spacing (0-16px), slot internal padding (2-16px), and minimum slot width (180-450px) that apply instantly without app restart.
  - Added a statusbar visibility toggle ("Show Statusbar at bottom") that reacts in real-time.
  - Redesigned `CarlaSettingsW` dialog styling with sleek Catppuccin Mochaccino sidebar navigation and modern form card layouts.

### 2026-10-13 03:42:00
- **feat(rack)**: Increase vertical Y-spacing margin between racklist items
  - Configured `RackListWidget.setSpacing(4)` to provide clean 4px vertical margins separating rack slots.

### 2026-10-13 03:39:00
- **feat(rack)**: Increase top and bottom vertical padding of racklist items
  - Increased `PluginSlot_Minimal` vertical contents margins from 3px to 6px (`(14, 6, 6, 6)`).
  - Adjusted slot `getFixedHeight` computation across compacted, knobs, and sliders views to comfortably accommodate the increased vertical spacing without clipping.

### 2026-10-13 03:35:00
- **feat(rack)**: Lower `RackListItem.kMinimumWidth` hard floor from 620px to 200px
  - Reduced `RackListItem.kMinimumWidth` and `RackListWidget.minimumWidth` constraint from 620px to 200px, eliminating the hard floor that prevented rack items and splitters from resizing smaller.
  - Reduced parameter name label minimum width in `SliderParamWidget` from 85px to 40px for compact slider layouts.

### 2026-10-13 03:32:00
- **fix(patchbay)**: Guard `act_canvas_side_by_side` initialization during startup `loadSettings`
  - Fixed `AttributeError: 'HostWindow' object has no attribute 'act_canvas_side_by_side'` during startup settings restoration.
  - Deferred side-by-side state loading until after canvas actions are initialized in `HostWindow.__init__`.

### 2026-10-13 03:30:00
- **feat(rack)**: Lower minimum width of rack items to 200px
  - Reduced `PluginSlot_Minimal` minimum width constraint from 260px down to 200px.
  - Allowed type badge and preset selector combo box to flexibly compress down to 44px and 50px respectively, maximizing rack compaction.

### 2026-10-13 03:26:00
- **feat(rack)**: Place minimize button to the right of the modernized meters
  - Arranged the header layout so the modernized LED and vertical peak meter slice appears before the minimize button, placing the minimize button directly to the right of the meters.

### 2026-10-13 03:25:00
- **feat(rack)**: Swap modernized meters slice and minimize button positions
  - Swapped layout positions so the minimize/collapse button sits next to the sliders/knobs toggle, and the modernized 2x2 LED / vertical peak meter slice is positioned at the far right.
  - Preserved the clean FontAwesome Nerd Font glyph icons (`\uf0c9` / `\uf1de`) for the sliders/knobs view toggle.

### 2026-10-13 03:15:00
- **feat(rack)**: Polish modernized 2x2 LEDs and rounded vertical peak meter slice
  - Fixed `LEDButton` scaling to accurately render SVGs/pixmaps within its bounded widget rectangle without overflowing or resetting custom dimensions.
  - Styled `_modern_slice_container` with a rounded pill background and subtle border, perfectly sizing the 2x2 grid and vertical peak meters without clipping.

### 2026-10-13 03:10:00
- **fix(project)**: Ensure audio engine backend initialization before startup autoload
  - Fixed startup project autoloading for `.carjp` and recent files by initializing backend engine state before dispatching project load requests.
  - Added structured `SESSION` logger diagnostics for project file conversion and backend loading.

### 2026-10-13 02:49:00
- **feat(rack)**: Modernized rack item slice with 2x2 mini LED circle grid and vertical peak meters
  - Implemented compact vertical slice housing audio/MIDI activity LEDs arranged in a 2x2 grid (8px rounded circles).
  - Configured slim vertical slice peak meters fitting within header height margins.
  - Added an Appearance context menu toggle ("Modernized Header Slice") with per-rack-slot state persistence.

### 2026-10-13 02:35:00
- **feat(ui)**: Pre-emptively hide main window on confirmed exit
  - Triggered immediate `hide()` and event flushing on closeEvent after exit confirmation to eliminate destruction lag and UI tearing during teardown.

### 2026-10-13 02:30:00
- **feat(project)**: Full Carla JSON project (`.carjp`) integration across open/save, recents, and drag-and-drop
  - Added support for `.carjp` in Recent Projects menu with automatic path preservation.
  - Enabled double-clicking `.carjp` files in the file browser tree and drag-and-drop loading into rack/canvas.
  - Updated Save/Save As dialog to respect `.carjp` file filter and automatically append the proper extension.
  - Added plugin crash pre-check and bridged execution support for JSON project files during load.
  - Registered `application/x-carla-project-json` MIME type in `data/carla.xml` and `data/desktop/carla.desktop`.

### 2026-10-13 02:18:00
- **feat(ui)**: Hideable menubar with global Ctrl+M, hamburger tool button, and toolbar context menu
  - Bound `Ctrl+M` to `HostWindow` with `Qt.WindowShortcut` context so it works globally even when the menubar is hidden.
  - Managed embedded `QWidgetAction` visibility so the "☰" hamburger menu tool button shows immediately on the toolbar when the menubar is hidden.
  - Added right-click context menu to the toolbar to easily toggle menubar and toolbar visibility.
  - Persisted `ShowMenubar`, `SideBySideEnabled`, and `SideBySideSizes` splitter ratio across application sessions.

### 2026-10-13 01:57:00
- **feat(patchbay)**: Adaptive zoom-dynamic dot grid and canvas cable line scaling
  - Replaced fixed dot spacing with an adaptive multi-tier LOD grid that scales dot frequency and radius based on zoom level.
  - Added subtle major grid reference lines at higher zoom levels for enhanced spatial orientation.
  - Made canvas cable lines scale smoothly across zoom levels with sub-pixel thickness dampening.
  - Added relative luminance contrast check for cable lines against canvas background, dynamically boosting or lowering lightness to guarantee clear contrast (>= 2.5:1).
  - Fixed `NameError: name 'QPen' is not defined` in `scene.py` and reduced dot grid opacity to a subtle background level.

### 2026-10-13 01:49:00
- **fix(patchbay)**: Implement missing single-node power and bypass action slots on context toolbar
  - Resolved `AttributeError: 'CanvasContextToolBarOverlay' object has no attribute '_slot_toggle_power'` by implementing `_slot_toggle_power` and `_slot_toggle_bypass`.
  - Added full rack plugin state sync and canvas scene update on toggle.

### 2026-10-13 01:34:00
- **feat(patchbay)**: Persist and restore hide-unused-ports state on save and serialization
  - Added dedicated `setHideUnconnectedPorts(hide)` method to `CanvasBox` with automatic port layout re-calculation and scene repaint.
  - Added multi-selection batch toggle button for hiding unconnected ports to the top context toolbar.
  - Deferred execution of the hide unconnected ports toggle in `restoreGroupPositions()` so that nodes spawn with standard initial bounds before collapsing unused ports.

### 2026-10-13 01:25:00
- **feat(patchbay)**: Move shortcuts help to toolbar tooltip and collapse overlay by default
  - Collapsed the floating cheat-sheet overlay by default to reduce visual clutter on launch.
  - Added a dedicated Help icon button (`nf-fa-question-circle`) to the left toolbar with a rich HTML tooltip displaying all patchbay and cable shortcuts on hover.


- **feat(patchbay)**: Sensible Nerd Font icon glyphs and quick color preset swatch popup menu
  - Audited and updated all toolbar glyphs across left palette and top context bar to high-readability, standardized Nerd Font icons (`mouse-pointer`, `select-drag`, `hand-paper`, `magnet`, `power-off`, `random`, `sliders`, `desktop`, `paint-brush`, `trash`, etc.).
  - Added quick popup color swatch menu for node tinting with Catppuccin presets (`Default Dark`, `Crimson`, `Synth`, `Audio`, `MIDI`, `FX`, `Dynamics`, `Teal`, `Sky`, `Flamingo`), Reset, and Custom Color Picker dialog.
  - Exported `QIcon` in `qt_compat.py` across PyQt5 and PyQt6 environments.

### 2026-10-13 01:18:00
- **feat(patchbay)**: Align toolbar icons with exact user Nerd Font FontAwesome codepoints
  - Updated all Left Palette and Top Context Toolbar buttons to the user's exact specification (`nf-fa-mouse-pointer`, `nf-fa-object-group`, `nf-fa-th`, `nf-fa-magnet`, `nf-fa-thumb-tack`, `nf-fa-check-square-o`, `nf-fa-toggle-on`, `nf-fa-cubes`, `nf-fa-pencil`, `nf-fa-trash`, `nf-fa-chain-broken`, `nf-fa-arrows-h/v`, etc.).

### 2026-10-13 01:12:00
- **feat(patchbay)**: Transform top context toolbar into compact icon-only palette with expanded actions
  - Replaced bulky text labels with sleek 26x26 square icon buttons and rich contextual tooltips.
  - Added Power (Active/Mute) and Bypass (Dry/Wet) toggles for plugins.
  - Added color picker dialogs (`QColorDialog`) for single and batch node tinting.
  - Added node properties dialog shortcut and toggle for hiding unconnected ports.
  - Added batch power, batch bypass, and alignment/repulsion actions for multi-node selection.

### 2026-10-13 00:54:00
- **fix(patchbay)**: Resolve empty top context toolbar on selection update
  - Fixed Qt layout collapsing to minimal empty margins during dynamic clear/rebuild by explicitly sizing items via font metrics and unparenting discarded widgets.
  - Ensured top context toolbar correctly displays actions for canvas (unselected), single node, and multiple nodes.

### 2026-10-13 00:45:00
- **feat(patchbay)**: Separate grid visibility from coordinate snapping and implement complete context toolbar actions
  - Separated `options.grid_enabled` (dot grid visual background) and `options.snap_enabled` (coordinate snapping) into independent toggle controls.
  - Added dedicated Grid button and Magnet Snap button to the left navigation tool palette.
  - Expanded top context actions toolbar (`CanvasContextToolBarOverlay`):
    - Single node selection: Edit, Custom UI, Jump to Rack, Clone, Rename, Remove, Split/Join box group, Disconnect All, Arrange Connected, Park Aside, Deselect.
    - Multiple node selection: Align Horiz, Align Vert, Distribute H, Distribute V, Auto-Repel Selected, Disconnect Selected cables, Invert Selection, Deselect.

### 2026-10-13 00:38:00
- **feat(patchbay)**: Split canvas toolbars into dedicated left navigation palette and dynamic top context actions bar
  - Resolved Qt6 `QMouseEvent.globalPos()` AttributeError by implementing `_get_event_global_pos()` using `globalPosition().toPoint()`.
  - Fixed button icon centering and zero-padding alignment across floating toolbars.
  - Re-exported graph utility functions (`arrange`, `repelNodes`, `moveAsideNonConnectedNodes`, `alignSelected`, etc.) from `patchcanvas.__init__.py`.
  - Added `CanvasContextToolBarOverlay` at top-center of the canvas dynamically reflecting selection state:
    - *0 nodes*: Global Auto-Arrange, Repel Overlaps, Park Disconnected, and Select All.
    - *1 node*: Node actions (Edit, Custom UI, Jump to Rack, Clone, Remove, Arrange Connected, Park Aside).
    - *2+ nodes*: Multi-node alignment (Align H/V, Distribute H/V, Auto-Repel Selected, Invert Selection, Deselect).

### 2026-10-13 00:23:00
- **feat(patchbay)**: Photoshop-style vertical floating toolbar on left canvas margin
  - Converted `CanvasToolBarOverlay` to a vertical column floating on the left side of the patchbay canvas.
  - Expanded tools with Auto-Arrange, Auto-Repel, Move Aside Non-Connected, Zoom In, Zoom Out, and Zoom to Fit.
  - Maintained smooth drag repositioning and dark translucent Catppuccin theme styling with subtle dividers.

### 2026-10-13 00:19:00
- **fix(patchbay)**: Fix NameError for `options` in `PatchScene.drawBackground`
  - Added missing `options`, `ceil`, `QColor`, and `QBrush` imports to `scene.py` preventing crashes during canvas background repaints.

### 2026-10-13 00:15:00
- **fix(patchbay)**: Immediate cable gradient refresh on node color change
  - Force-repainted connected cable lines and scheduled an instant scene redraw inside `CanvasBox.setCustomColor()`, updating gradient endpoints immediately without requiring node repositioning.

### 2026-10-13 00:14:00
- **feat(patchbay)**: Physics-based iterative auto-repel tools
  - Added `repelNodes()` with AABB overlap resolution and configurable padding/iterations.
  - Added "Auto-Repel (Selected)" and "Auto-Repel (All)" options to the canvas box "Arrange & Align" context menu.

### 2026-10-13 00:11:00
- **feat(patchbay)**: Subtle canvas alignment dot grid and coordinate snapping
  - Added background alignment dot rendering in `PatchScene.drawBackground()` with adaptive contrast according to canvas theme luminance.
  - Implemented node drag snapping to the grid via `CanvasBox.fixPos()`.
  - Added automatic grid snapping to `alignSelected()` operations (`horizontal`, `vertical`, `distribute_h`, `distribute_v`).

### 2026-10-13 00:08:00
- **fix(patchbay)**: Synchronize minimap preview bounds with infinite canvas scene limits
  - Dynamically updated `fRenderSource` and `fInternalRatio` in `CanvasPreviewFrame` to match expanding `sceneRect()` bounds.
  - Calculated `setViewSize` proportions relative to the live scene bounding box rather than static initial canvas dimensions.

### 2026-10-13 00:01:00
- **fix(patchbay)**: Resolve `CanvasBox.calculateBoxSize` AttributeError
  - Aliased `calculateBoxSize` to `updatePositions` on `CanvasBox` and directly invoked `updatePositions` on toolbar toggle and project restore.

### 2026-10-12 23:55:00
- **feat(patchbay)**: Infinite canvas, legacy project migration, and side-by-side layout persistence
  - Implemented dynamic scene and bounds expansion (`canvas.size_rect`, `sceneRect()`) in `canvasbox.py` and `scene.py` removing fixed boundary clamping for an infinite canvas experience.
  - Automatically recenters legacy save files lacking `infinite_canvas = true` upon load while preserving exact coordinates for modern infinite canvas projects.
  - Added canvasbox sub-bar button (`\uf066` / `\uf065`) to dynamically collapse and hide unconnected ports.
  - Tightly grouped unconnected nodes within cluster bounds when triggering "Move Aside Non-Connected Nodes".
  - Persisted `infinite_canvas`, `hide_unconnected_ports`, and side-by-side split view layout state (`split_view_enabled`, `split_view_sizes`) across XML and JSON formats.

### 2026-10-12 23:28:00
- **feat(ui)**: Enlarged FontAwesome Nerd Font icons and TODO tracker update
  - Increased font-size for action buttons (`b_power`, `b_bypass`, `b_gui`, `b_edit`, `b_slider_mode`, `b_minimize`) from 11px to 13px (12px on minimize) for enhanced legibility.
  - Increased canvas box toolbar button icon font size to 9pt on 18×18 square targets.
  - Checked off canvas box sub-bar action buttons in `TODO.md`.

### 2026-10-12 23:26:00
- **feat(ui)**: Pure FontAwesome Nerd Font buttons and transparent button styling
  - Converted Power (`\uf011`), Bypass (`\uf05e`), Custom UI (`\uf2d0`), and Parameters/Edit (`\uf013`) into pure `QPushButton` controls using FontAwesome Nerd Font glyphs.
  - Eliminated static background fills across all header buttons (Bypass, Expand/Minimize, Power, GUI, Edit, Slider mode) for a clean, borderless transparent look.
  - Added subtle hover (`0.08`) and pressed (`0.16`) translucent feedback without distracting borders or hard backgrounds.

### 2026-10-12 23:22:00
- **feat(ui)**: Clean borderless buttons, consistent type badge width, and FontAwesome / Nerd Font glyphs
  - Removed all button border outlines in both Rack headers and Canvas boxes for a clean, minimal look.
  - Standardized the Type Badge width to 56px with centered alignment so plugin titles align uniformly.
  - Converted minimize/expand (`\uf077` / `\uf078`) and slider view toggles (`\uf0c9` / `\uf1de`) to FontAwesome / Nerd Font icons with 22×22 square sizing.
  - Kept Custom UI button (`b_gui`) always visible, transitioning into a disabled state when unavailable.

### 2026-10-12 23:15:00
- **feat(ui)**: Standardized square action buttons, Nerd Font icons, and responsive header layout
  - Fixed action buttons (`b_enable`, `b_bypass`, `b_gui`, `b_edit`) to consistent square dimensions (22×22 px in rack slots, 18×18 px in canvas boxes) with 3 explicit states: Active (accent glow/border), Inactive (neutral subtle border), and Disabled/Unavailable (greyed out `opacity: 0.35`).
  - Unified iconography with FontAwesome / Nerd Font glyphs across Canvas and Rack headers (`\uf011` Power, `\uf05e` Bypass, `\uf08e` Jump to Rack).
  - Repositioned the category/type badge pill before the plugin name in the rack header for uniform left title alignment.
  - Reduced minimum width constraints (down to 260px) and set preset selector sizing for responsive layout fitting on smaller screens.
  - Added comprehensive tooltips to all header buttons, type badge, and preset controls.

### 2026-10-12 23:00:00
- **feat(rack)**: CarlaSkin 2-line headers and canvas-style buttons
  - Restructured plugin slot headers into a 2-line layout: Line 1 aligns the plugin title, type badge, peak meters, and minimize toggle; Line 2 provides a dedicated action toolbar for power, bypass, GUI, edit, presets, and slider mode.
  - Increased left margin padding to give the category colorbar generous separation from the controls.
  - Upgraded rack buttons to mirror canvas box aesthetics with neutral translucent backgrounds (`rgba(255, 255, 255, 0.05)`), subtle borders (`0.12`), hover highlights, and crisp pressed feedback.
  - Resolved plugin active state synchronization between patchbay canvas toolbar and host engine/rack widget (`pwidget.setActive(..., sendHost=True)`).
  - Toggling power now updates the DSP engine, rack UI enable toggle, and canvas node simultaneously.
- **feat(patchbay)**: Toolbar button visuals and tactile feedback
  - Removed darker shading and dividing line behind canvas box toolbar buttons for a seamless transparent look.
  - Added interactive visual feedback for buttons including hover glow, distinct pressed background highlight, and tactile 1px offset shift.

### 2026-10-12 22:22:00
- **feat(patchbay)**: Neutral square toolbar styling
  - Adjusted sub-bar height to 22px and rendered 14×14 square buttons with 4px top/bottom padding.
  - Replaced colored fills with unified neutral translucent backgrounds, subtle borders, and muted icon tints.

### 2026-10-12 21:50:00
- **feat(patchbay)**: Semantic Bypass button and "Jump to Rack" context menu
  - Preserved the native top-left icon (`CanvasIcon`) completely undisturbed; plugin titles display with clean padding.
  - Added "Jump to Rack" to the node right-click context menu for all rack plugins, focusing and scrolling the paired rack item smoothly without header clutter.
  - Placed the compact, semantic power toggle (`⏻`) neatly on the right next to the category badge pill, rendering only for plugins that expose bypass capabilities.
  - Ensured clicking bypass toggles the active state in-place without triggering selection sync or shifting views.


- **refactor(cli)**: Modernize command-line argument parsing with `argparse.ArgumentParser`
  - Replaced legacy manual `sys.argv` string inspection loop in `handleInitialCommandLineArguments()` with standard `argparse.ArgumentParser` and `parse_known_args()`.
  - Unified host options and `CarlaLogger` configuration (`--log-level`, `--log-whitelist`, `--log-blacklist`, `--console-log`, `--no-console-log`) into a single declarative parser.
  - Safely handles positional project files, OSC URLs, and unknown backend pass-through flags without errors.
  - Automatically loads plugins in bridge mode and selects newer autosaves without prompt dialogs when `--autoload-lastsave` is active.

- **docs(cli)**: Rich colored help banner with app info, versions, and full tag options
  - Added Carla version header, Python, Qt, PyQt version specs, and binary/resource paths directly inside `--help`.
  - Added ANSI color highlighting for options, arguments, and tags.
  - Listed all available logging filter tags (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`) in `--log-whitelist` and `--log-blacklist`.
  - Added binary stream decoding and control-character sanitization to stderr capture in `CarlaLogger`.
  - Wired explicit debug level forwarding from `log_carla()` through `DEBUG_LEVEL_MAP` to prevent suppression leaks.

- **refactor(logging)**: Deduplicate repeated messages and filter non-fatal backend assertion noise
  - Added consecutive log deduplication in `CarlaLogger` with repeat counting to prevent runaway spam in console output.
  - Filtered benign C++ backend assertions (`canRead`, `groupName != nullptr`, `TemporaryFile`, buffer sizes, `plugin.get() != nullptr`) to debug level.
  - Suppressed yabridge/Wine boilerplate, duplicate LV2 plugin notices, `carla_v3_component_handler` queries, and `PatchCanvas::removeGroup` warnings on shutdown.
  - Demoted high-frequency port discovery, client addition, and connection callback messages (`addPort`, `connectPorts`, `slot_handlePatchbayClientAddedCallback`, `addGroup`, `unhiding box`) to debug level, keeping default info level clean.

- **feat(patchbay)**: Add type-based node selection to patchbay context menus
  - Implemented `getNodeBadgeType()` on `CanvasBox`, mapping each node to its exact functional type (`SYNTH`, `EQ`, `DELAY`, `FILTER`, `DIST`, `DYN`, `MOD`, `UTIL`, `FX`, `PLUGIN`, `SINK`, `SOURCE`, `IN`, `OUT`, `HW`, `APP`, `NODE`).
  - Added "Select All of Same Type ({type})" to individual node context menus.
  - Added "Select -> By Type" dynamic submenu to both canvas background and node item context menus.
  - Added `selectNodesByType(target_type)` and `getAvailableNodeTypes()` in `patchcanvas.py`.

- **feat(patchbay)**: 100% badge coverage across all plugins, external clients, and I/O nodes
  - Added fallback badges `PLUGIN` (Blue) and `SYNTH` (Red) for plugins without explicit category tags.
  - Added `APP` (Mauve) for bidirectional client apps and `NODE` (Slate) fallback, guaranteeing every node displays a badge.

- **feat(patchbay)**: Add header badge pills for sinks, sources, hardware, and inputs/outputs
  - Implemented dynamic role detection in `canvasbox.py` for non-plugin nodes.
  - Added color-coded badges: `SINK` (Green), `SOURCE` (Peach), `IN` (Sky), `OUT` (Yellow), and `HW` (Lavender) alongside existing category badges.

- **feat(patchbay)**: Neutral default nodes with clean category badges in header
  - Removed forced default category coloring so unstyled nodes and rack items remain clean and neutral by default.
  - Implemented crisp, color-coded category pill badges (e.g. `SYNTH`, `FX`, `EQ`, `DYN`, `UTIL`) inside patchbay node headers for instant visual classification without cluttering or tinting the whole node.

- **fix(color)**: Properly reset patchbay node color to default category tone when rack item color is reset
  - Updated `changePluginColor()` in `carla_host.py` to restore the node's Catppuccin category color when resetting a rack item rather than leaving it in an unsynced state.
  - Updated `getColorAndSkinStyle()` and `createPluginSlot()` in `carla_skin.py` to cleanly revert to the category palette whenever `CarlaColor` is reset to `"255;255;255"`.

- **feat(patchbay)**: Support individual color customization and persistence for non-rack patchbay items
  - Enabled color selection and persistence for all patchbay items (e.g. ALSA, JACK, PipeWire hardware, external clients) via canvas positions metadata in `patchcanvas.py` and `project_storage.py`.
  - Serialized custom node colors into project files (`.carxp`, `.carjp`, `.json`) under canvas group position tags.
  - Prioritized mapped rack item colors on load so synced rack items always govern their canvas counterparts while standalone nodes retain their independently assigned colors.

- **feat(patchbay)**: Improve node header readability with soft color tinting and adaptive contrast text
  - Blended 35% custom color tint with base header background in `canvasbox.py` for distinct, non-garish node headers.
  - Added custom color accent divider line under node headers.
  - Implemented dynamic luminance calculation for node header text to guarantee high contrast and readability against tinted headers.

- **fix(color)**: Bidirectional saved color synchronization on project load & vibrant category palettes
  - Updated `getColorFromCategory()` in `carla_skin.py` to use vivid Catppuccin category tones instead of dark gray shades, giving unstyled nodes and rack items distinct colors immediately.
  - Aligned rack context menu structure by elevating Color submenu to the top level, matching canvas node context menus with direct `QColorDialog` triggers.
  - Synchronized colors directly from rack widgets (`fSkinColor`) to patchbay canvas nodes on both `PluginListItem.recreateWidget()` and `slot_handlePatchbayClientAddedCallback()`.

- **fix(canvas)**: Preserve active selection on canvas right-click and add Select menu to node context menu
  - Prevented right-click mouse press and release on canvas background from deselecting highlighted items in `scene.py`.
  - Added "Select" submenu (`Select All`, `Deselect`, `Invert Selection`) to both canvas background and node item context menus in `canvasbox.py`.

### 2026-10-12 16:40:00 (`86543b139`)
- **feat(canvas)**: Add patchbay selection shortcuts and context menu actions
  - Implemented `Ctrl+A` (Select All), `Ctrl+D` (Deselect All), and `Ctrl+Shift+I` (Invert Selection) in `DraggableGraphicsView`.
  - Added dedicated "Select" submenu in the patchbay background context menu exposing all selection actions.
  - Implemented `selectAllNodes()`, `deselectAllNodes()`, and `invertNodeSelection()` helpers in `patchcanvas.py`.

### 2026-10-12 16:30:00 (`ff593af74`)
- **fix(canvas)**: Prevent blurry text rendering on patchbay ports and box titles
  - Rounded text coordinates to integer pixel positions in `canvasport.py` and `canvasbox.py` to eliminate subpixel coordinate blur under OpenGL viewports.
  - Temporarily disabled geometric polygon antialiasing right before invoking `painter.drawText()`, allowing font rasterization to utilize sharp native hinting instead of multisample edge blurring.

### 2026-10-12 16:23:15 (`2357653cc`)
- **fix(canvas)**: Enable 4x MSAA hardware multisampling for OpenGL canvas viewport
  - Configured `QSurfaceFormat` with 4 samples on `QOpenGLWidget` when canvas antialiasing is enabled, resolving jagged lines and missing antialiasing when using OpenGL hardware acceleration.
  - Exported `QSurfaceFormat` in `qt_compat.py`.

### 2026-10-12 18:30:00
- **fix(rack)**: Fix persistence and startup synchronization of saved plugin colors on canvas nodes
  - Added project dirty tracking and `markProjectModified()` on `changePluginColor()` to ensure custom colors persist on save.
  - Linked `setGroupAsPlugin()` in `patchcanvas.py` to fetch saved `CarlaColor` custom data from the engine and immediately tint the patchbay node and its cable connections upon project loading.

### 2026-10-12 18:58:00
- **feat(patchbay)**: Assign distinctive Catppuccin category colors to nodes by default and sync saved colors
  - Added default Catppuccin category color palette mapping (Synth: Red, Delay: Sky, EQ: Green, Filter: Teal, Distortion: Peach, Dynamics: Yellow, Modulator: Mauve, Utility: Lavender, Other: Blue) for patchbay nodes without explicit custom overrides.
  - Linked `CarlaColor` retrieval in `setGroupAsPlugin()` to restore project-saved custom node tints reliably upon initial load.

### 2026-10-12 18:24:00 (`e577fae12`) (`e577fae12`)
- **fix(canvas)**: Ensure cable gradients render regardless of line formula (bezier/straight/stepped) and stroke pattern
  - Recomputed `updateLineGradient()` on every `updateLinePos()` to ensure gradients always match latest node positions.
  - Fixed painter rendering in `CanvasLine.paint()` to draw directly with `_cached_pen` preserving `QBrush` gradient fill across all line shapes and stroke patterns (`solid`, `dotted`, `dashed`).

### 2026-10-12 18:20:00 (`ceaa6b6e1`)
- **fix(canvas)**: Fix cable linear gradients not rendering across canvas nodes
  - Resolved gradient vector calculation in `CanvasLine.updateLineGradient()` by mapping scene port bounding rect endpoints into the item's local coordinate system (`mapFromScene()`).
- **feat(rack)**: Add unified Catppuccin color palette and custom color picker to rack item menu
  - Replicated horizontal Catppuccin preset palette into rack `Appearance -> Color` context menu.
  - Added "Custom Color..." `QColorDialog` picker and "Reset Color" to both patchbay node and rack context menus.
  - Synchronized color changes bidirectionally between rack items and `group.widgets` on the patchbay canvas.
  - Applied subtle 15% custom tint formula to patchbay node body backgrounds to match rack styling.

### 2026-10-12 17:57:00 (`2f3ba4308`)
- **fix(rack)**: Fix bidirectional color synchronization between patchbay nodes and rack items
  - Connected `ACTION_PLUGIN_COLOR` to `changePluginColor()` to update rack skins with the selected Catppuccin color and persist to `CarlaColor`.
  - Added reverse synchronization from `changePluginColor()` to `CanvasBox.setCustomColor()` on patchbay nodes.

### 2026-10-12 17:53:00 (`4dab86fee`)
- **feat(rack)**: Synchronize node colors between patchbay and rack items
  - Added `ACTION_PLUGIN_COLOR` to patchcanvas callback architecture and notified when `setCustomColor()` is changed on a plugin node.
  - Linked `canvasCallback` to propagate the custom tint color to the corresponding `PluginListItem` in the rack.

### 2026-10-12 17:47:00 (`f5ca2fe6a`)
  - Added "Color" submenu to node context menu with horizontal one-click Catppuccin color buttons (Red, Peach, Yellow, Green, Teal, Sky, Blue, Lavender, Mauve, Pink) and reset button.
  - Linked custom node colors into `CanvasLine.updateLineGradient()`, dynamically tinting connection cable gradients to match source and target node colors.

### 2026-10-12 17:42:00 (`ef964798a`)
- **feat(patchbay)**: Implement dynamic source-to-destination gradient coloring along cables
  - Updated `CanvasLine.updateLineGradient()` to construct `QLinearGradient` directly oriented between output and input port endpoints (`scenePos()`).
  - Smoothly interpolates the cable color between the source port color at 0.0 and destination port color at 1.0.

### 2026-10-12 17:36:00 (`dd3cab7d0`)
  - Fixed `NameError: name 'QComboBox' is not defined` when opening Carla Settings dialog by importing `QComboBox`, `QSlider`, and `QSpinBox` via `qt_compat.py`.
  - Added `QSpinBox` to Qt5 and Qt6 exports in `qt_compat.py`.

### 2026-10-12 17:34:00 (`38b2215df`)
- **feat(canvas)**: Expose line style, pattern, and opacity in Canvas Settings
  - Added configurable options `Canvas/LineStyle` (`"bezier"`, `"straight"`, `"stepped"`), `Canvas/LineStroke` (`"solid"`, `"dotted"`, `"dashed"`), and `Canvas/LineOpacity` (20% - 100%) in `carla_shared.py`, `patchcanvas/__init__.py`, and `carla_host.py`.
  - Added line style and pattern comboboxes and an interactive opacity slider in `carla_settings.py`.
  - Updated `CanvasLine` to dynamically scale line alpha by user opacity settings.
- **refactor(qt)**: Complete migration of all custom UI widgets in `widgets/` to `qt_compat.py`
  - Exported missing UI items (`QKeySequence`, `QShortcut`, `QListWidget`, `QSvgWidget`, `QToolButton`, `QDial`, `QConicalGradient`, `QProgressBar`, `QGraphicsSimpleTextItem`, `QActionGroup`) in [`qt_compat.py`](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/qt_compat.py).
  - Cleaned up `if qt_config == 5:` boilerplate across all 13 widget modules in `widgets/` (`draggablegraphicsview.py`, `canvaspreviewframe.py`, `pixmapdial.py`, `scalabledial.py`, `commondial.py`, `digitalpeakmeter.py`, `paramspinbox.py`, `pianoroll.py`, `racklistwidget.py`, `scalablebutton.py`, `ledbutton.py`, `collapsablewidget.py`, `pixmapkeyboard.py`).

### 2026-10-12 17:11:00
- **fix(qt)**: Resolve `qt_config` NameError in `theme.py` and clean up `canvasbox.py`
  - Replaced manual `qt_config == 6` branches in `theme.py` (`parse_pen`, font weight) with standard `Qt` pen style and `QFont.Bold` / `QFont.Normal` aliases.
  - Added `QImage.Format_ARGB32` and `QImage.Format_RGB32` aliases to `qt_compat.py`.
  - Removed obsolete runtime `qt_config` imports in `canvasbox.py` inline display and `itemChange`.

### 2026-10-12 17:09:00
- **refactor(qt)**: Centralize Qt5/Qt6 imports through `qt_compat.py` across `patchcanvas`
  - Exported missing Qt items (`QGraphicsPathItem`, `QGraphicsLineItem`, `QGraphicsObject`, `QGraphicsDropShadowEffect`, `QFontMetrics`, `QPolygonF`, `pyqtSignal`, `pyqtSlot`, `qFatal`, `qWarning`, `QAbstractAnimation`, `QGraphicsSvgItem`, `QSvgRenderer`, `QFormLayout`, `QGroupBox`, `QTabWidget`, `QTableWidget`, `QTableWidgetItem`) in [`qt_compat.py`](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/qt_compat.py).
  - Replaced repetitive `if qt_config == 5: from PyQt5... elif qt_config == 6: from PyQt6...` import boilerplate across all `patchcanvas` modules with direct `from qt_compat import ...`.

### 2026-10-12 17:03:00
- **refactor(canvas)**: Unify line drawing and Bézier formulas into single configurable `CanvasLine`
  - Re-implemented `CanvasLine` as a flexible `QGraphicsPathItem` supporting orthogonal geometry `shape` (`"bezier"`, `"straight"`, `"stepped"`) and stroke pattern (`"solid"`, `"dotted"`, `"dashed"`).
  - Maintained backward-compatible `CanvasBezierLine` subclass alias and stub module.
  - Eliminated duplicate boilerplate across line implementations while enabling future custom path and stroke styling.

### 2026-10-12 16:53:00
- **perf(canvas)**: Cache gradient `QPen` in `CanvasBezierLine`/`CanvasLine` - built once in `updateLineGradient()`, reused in `paint()`. Eliminates hundreds of `QPen`/`QLinearGradient`/`QColor` heap allocs per mousemove tick with many connections.
- **perf(canvas)**: Early-return in `updateLineSelected()` when selection state is unchanged - skips full gradient recompute on every drag event when nothing visually changed.
- **perf(canvas)**: Guard cosmetic double-draw (glow overlay) in line `paint()` behind `options.eyecandy` - saves one full path/line draw per connection per frame when eye candy is off.
- **perf(canvas)**: Cache theme attribute lookups in `CanvasPort` - resolved once at port creation and on `updateTheme()` instead of dict-instantiation + `getattr` f-string lookups on every `paint()` frame for every visible port.
- **perf(canvas)**: Throttle minimap update timeout from 0ms to 150ms - stops full scene re-renders for the thumbnail on every event.
- **perf(canvas)**: Reduce `CanvasBoxShadow` blur radius from 20 → 8 - cuts per-box offscreen composite buffer cost.

### 2026-10-12 15:59:00 (`3f3c6711c`)
- **perf(canvas)**: Remove `repaintLines()` cascade from `CanvasBoxShadow.draw()` - eliminates per-frame `updateLinePos()` call on every box shadow repaint, which was cascading into O(connections) work every render tick when dragging nodes with many connections loaded.

### 2026-10-12 15:37:00 (`e213d7f02`)
- **fix(canvas)**: Fix HighQualityAntialiasing crash and expose Use OpenGL in Canvas settings
  - Fixed `AttributeError: type object 'QPainter' has no attribute 'HighQualityAntialiasing'` on Qt6 by safely probing `QPainter.RenderHint`.
  - Exposed "Use OpenGL for rendering (needs restart)" directly in **Settings → Canvas → Rendering** with bidirectional state synchronization to the Experimental tab.

### 2026-10-12 15:26:30 (`e225021e5`)
- **perf(canvas)**: Optimize patchbay rendering with SmartViewportUpdate and eliminate event hot path logging
  - Upgraded graphicsView viewport update mode to `SmartViewportUpdate` for intelligent partial blits when dragging nodes and cables.
  - Removed per-click and per-miss verbose `log_carla` calls in `CanvasViewportFilter` to prevent hot-path I/O stalls during interaction.
  - Streamlined cable render pipeline in `CanvasBezierLine.paint` by removing redundant double path stroking.

### 2026-10-12 15:20:45 (`6c4960fc0`)
- **fix(ui)**: Fix rack plugin removal across all skins and enable empty canvas left-click drag panning
  - Connected `b_remove` in `PluginSlot_Calf` and fixed `Delete` key handling in `RackListWidget` to invoke `self.host.remove_plugin()` with a confirmation prompt.
  - Implemented left-click drag panning on empty canvas area in `DraggableGraphicsView` for fluid navigation without needing to switch modal tools.

### 2026-10-12 15:09:12 (`b2ab7196b`)
- **fix(compat)**: Restore QSizePolicy in PyQt6 imports in qt_compat
  - Re-added `QSizePolicy` to the `PyQt6.QtWidgets` import list so `QSizePolicy.Policy` alias definitions resolve correctly on startup.

### 2026-10-12 15:07:45 (`839cdd56a`)
- **feat(ui)**: Add side-by-side split view and bidirectional rack-patchbay synchronization
  - Added toggleable Side-by-Side View mode (`Ctrl+Shift+R`) placing Patchbay (left) and Rack (right) in an adjustable `QSplitter` layout.
  - Implemented bidirectional selection sync: selecting a node in the Patchbay centers and scrolls to its slot in the Rack; selecting a slot in the Rack highlights and centers the node on the canvas.
  - Exported `QSplitter` and `QWidget` in `qt_compat.py` for cross-version Qt compatibility.

### 2026-10-12 14:34:44 (`5cac2b881`)
- **fix(session)**: Propagate dirty modifications on node moves, connects, and deletes
  - Wired `markProjectModified()` into `ACTION_GROUP_POSITION` moves so node relocations flag unsaved edits.
  - Linked cable connection / disconnection actions and backend plugin add / remove / rename callbacks to mark project state as modified.
  - Fixed exit prompt bypassing by ensuring dirty state triggers the Save/Discard/Cancel dialog.

### 2026-10-12 14:27:40 (`9e46f070a`)
- **feat(session)**: Add save on exit prompt, dirty state indicator, and autosave countdown timer
  - Implemented save-on-exit dialog with `Save`, `Discard`, and `Cancel` options when unsaved edits exist.
  - Added visual dirty indicator (`*` prefix in title bar and `● Unsaved` / `✓ Saved` status bar badge).
  - Added live statusbar timer displaying last autosave time and countdown to next autosave.

### 2026-10-12 14:19:02 (`d58a34d15`)
- **fix(logging)**: Capture C++ backend stderr into CarlaLogger
  - Intercepted file descriptor 2 (POSIX `stderr`) using `os.dup2` to capture C++ backend assertion failures and plugin bridge messages directly into `CarlaLogger`.
  - Started stderr capture at launcher startup in `source/frontend/carla`.

### 2026-10-12 09:58:45 (`ac84a74e5`)
- **fix(logging)**: Remove right padding on log levels, add per-tag colors, and handle backend assertion logs
  - Removed fixed right-padding on log level badges (e.g. `[INFO]`).
  - Added distinct color themes for all categories (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`).
  - Classified incoming `[carla]` assertion failures into `[BACKEND]` error logs.

### 2026-10-12 09:51:38 (`539c08c44`)
- **fix(logging)**: Import QFrame, QCheckBox, QLabel, QVBoxLayout in carla_host
  - Exported `QCheckBox` across PyQt5 and PyQt6 in `qt_compat.py`.
  - Resolved `NameError: name 'QFrame' is not defined` during host window initialization.

### 2026-10-12 09:45:02 (`621a4e998`)
- **feat(logging)**: Rich terminal output, tag filtering checklist, and mirror settings
  - Created centralized `CarlaLogger` supporting Python `rich` formatting, log levels, and categories.
  - Added CLI flags (`--log-level`, `--log-whitelist`, `--log-blacklist`, `--console-log`, `--no-console-log`).
  - Added in-UI Log tab tag checklist filter to dynamically toggle visible categories without losing log history.
  - Added setting checkbox to mirror application logs to terminal.

### 2026-10-12 04:01:07 (`5e318622a`)
- **fix(autosave)**: Prevent recursive nested autosave directories on recovery
  - Added `get_canonical_project_filepath` to normalize paths and strip `.autosaves/` segments when recovering.
  - Separated canonical project file path from recovery source override in `loadProjectNow`.
  - Pruned corrupted nested autosave directories and duplicate plugin folders.

### 2026-10-12 03:53:18 (`2de8b65f0`)
- **feat(patchbay)**: Add modal tools, floating toolbar, fix zoom minimap, and update interactions
  - Implemented Photoshop/Blender-style modal tools (`V` for marquee, `H` / `Space` for hand/pan, `Q` / `Escape` for pointer).
  - Added floating modal tool pill widget (`CanvasToolBarOverlay`) with cached Nerd Font glyphs.
  - Fixed minimap viewport coordinate mapping and zoom scale synchronization.
  - Made patchbay keyboard shortcut help overlay draggable across viewport.

### 2026-10-12 03:11:08 (`8bec393b0`)
- **fix(patchcanvas)**: Correct connection endpoint attribute names in moveAsideNonConnectedNodes
  - Fixed `AttributeError: 'connection_dict_t' object has no attribute 'group_id_1'`.

### 2026-10-12 03:06:24 (`e4c2b5be0`)
- **feat(patchcanvas)**: Add 'Move Aside Non-Connected Nodes' arrange action
  - Added background context menu option to shift unconnected nodes away from active graphs.

### 2026-10-12 03:00:16 (`f8bc296df`)
- **fix(patchcanvas)**: Fix mouse dragging for canvas panning, node movement, and right-drag marquee disambiguation
  - Restored canvas panning and item dragging without event swallowed in `DraggableGraphicsView`.
  - Added background click to deselect items.

### 2026-10-12 02:53:19 (`fae78c8d2`)
- **feat(patchcanvas)**: Fix right-drag marquee gesture, background deselect, and zoom-invariant line/selection widths
  - Device-pixel-invariant stroke widths for connection lines and node borders when zooming.

### 2026-10-12 02:40:54 (`60c3ac6a9`)
- **feat(patchcanvas)**: Add directional right-drag marquee selection and non-overlapping node alignment
  - Left-to-right drag selects all touched/intersected items; right-to-left drag selects enclosed items only.
  - Added repel spacing in horizontal and vertical alignment to avoid node overlap.

---

## [Unreleased] - 2026-10-06

### 2026-10-06
- **perf(patchbay)**: Debounce heavy canvas refresh during rack reordering (`3bdb33f11`)
  - Throttled canvas redraw triggers while drag-reordering rack items to eliminate UI stuttering.
- **refactor(rack)**: Native `moveRow` reordering without manual widget shuffling (`1b32d180a`)
  - Switched rack reordering to use native `QModelIndex::moveRow`, preventing Qt garbage collection segfaults.
- **fix(rack)**: Prevent list widget crashes and destruction during fast reordering (`a897cf0c5`, `fb6dd9261`, `c44f4161b`, `f57456a4e`)
  - Parked widgets in temporary holding container during moves rather than unparenting to `None`.
  - Preserved active rack selection state seamlessly during item drag-reordering.
- **feat(ui)**: Modern native rack buttons and Unicode symbol icons (`815691ce8`, `67e54e3b9`, `b7c76a47d`, `fb8318e89`)
  - Replaced overlapping power icons with native dark-themed `QPushButton` for bypass and minimize controls.
  - Updated UI iconography to clean Unicode symbols across compact and standard rack modes.

---

## [Unreleased] - 2026-10-05

### 2026-10-05
- **feat(packaging)**: Arch Linux / Pacman integration and PKGBUILD (`f8a2a6c79`, `9105b012b`, `8d4984256`)
  - Added native `PKGBUILD` for `carla-improved` package targeting Qt6.
  - Added helper `build.sh` script and `installation.md` guide for rapid building and pacman installation.
- **feat(session)**: Recent projects list and autoload on startup (`4da5fdaa8`)
  - Added `Recent Projects` submenu under `File` with file path previews.
  - Added startup prompt to resume last opened project and `--autoload-lastsave` CLI flag.
- **feat(patchbay)**: Canvas node quick search with fuzzy matching (`0f50c125f`)
  - Implemented `Ctrl+F` in-canvas search bar with fuzzy filtering and direct viewport centering.
- **feat(patchbay)**: Persistent canvas node coordinates in project files (`c79581357`)
  - Automatically saved and restored canvas node positions inside `.carxp` project files.
- **feat(ui)**: Blender-inspired socket aesthetics, rounded nodes, and system typography (`e4eeb3315`, `311e6d60c`)
  - Introduced circular socket styling, rounded canvas node containers, and refined port colors.
  - Unified system fonts across the interface and added initial CLI debug/logging flags.
- **feat(ui)**: Pianoroll enhancements and theme system (`a6acc8bd0`, `7ba0b3c45`)
  - Styled pianoroll view, upgraded keyboard bitmaps, and installed data-driven `themes.json`.
- **fix(patchbay)**: Patchbay rack node sync and PyQt6 inline display support (`65eaa7e6a`)
  - Fixed sync between rack items and canvas nodes, port drag connections, and PyQt6 inline display rendering.

---

## [Unreleased] - 2026-10-04

### 2026-10-04
- **fix(canvas)**: Initial patchbay canvas stability improvements (`831bf93b3`)
  - Fixed initial canvas rendering glitches, drag-connection line offsets, and view initialization.

