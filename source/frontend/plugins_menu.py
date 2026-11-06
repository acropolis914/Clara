#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Plugin menu actions, split out of host_app.py. HostWindow inherits this mixin.

from carla_app import QSafeSettings, gCarla
from carla_backend import (
    PLUGIN_CLAP,
    PLUGIN_DSSI,
    PLUGIN_JSFX,
    PLUGIN_LADSPA,
    PLUGIN_LV2,
    PLUGIN_OPTIONS_NULL,
    PLUGIN_OPTION_AVOID_BRIDGE,
    PLUGIN_OPTION_USE_BRIDGE,
    PLUGIN_SF2,
    PLUGIN_SFZ,
    PLUGIN_VST2,
    PLUGIN_VST3,
)
from carla_shared import (
    CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES,
    CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES,
    CARLA_KEY_MAIN_SYSTEM_ICONS,
    CARLA_KEY_PATHS_CLAP,
    CARLA_KEY_PATHS_DSSI,
    CARLA_KEY_PATHS_JSFX,
    CARLA_KEY_PATHS_LADSPA,
    CARLA_KEY_PATHS_LV2,
    CARLA_KEY_PATHS_SF2,
    CARLA_KEY_PATHS_SFZ,
    CARLA_KEY_PATHS_VST2,
    CARLA_KEY_PATHS_VST3,
    CARLA_KEY_WINE_AUTO_PREFIX,
    CARLA_KEY_WINE_EXECUTABLE,
    CARLA_KEY_WINE_FALLBACK_PREFIX,
    CustomMessageBox,
    log_carla,
)
from patchcanvas import patchcanvas
from qt_compat import QApplication, QCursor, QMenu, QMessageBox, QPointF, Qt, pyqtSlot


class PluginsMenuMixin:
    # --------------------------------------------------------------------------------------------------------
    # Plugins (menu actions)

    def showAddPluginDialog(self):
        # TODO self.fHasLoadedLv2Plugins
        if self.fPluginListDialog is None:
            hostSettings = {
                "showPluginBridges": self.fSavedSettings[
                    CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES
                ],
                "showWineBridges": self.fSavedSettings[
                    CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES
                ],
                "useSystemIcons": self.fSavedSettings[CARLA_KEY_MAIN_SYSTEM_ICONS],
                "wineAutoPrefix": self.fSavedSettings[CARLA_KEY_WINE_AUTO_PREFIX],
                "wineExecutable": self.fSavedSettings[CARLA_KEY_WINE_EXECUTABLE],
                "wineFallbackPrefix": self.fSavedSettings[
                    CARLA_KEY_WINE_FALLBACK_PREFIX
                ],
            }
            self.fPluginListDialog = d = gCarla.felib.createPluginListDialog(
                self.fParentOrSelf, hostSettings
            )
            if hasattr(d, "pluginAddRequested"):
                d.pluginAddRequested.connect(self.loadPluginFromInfo)

            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_LADSPA, self.fSavedSettings[CARLA_KEY_PATHS_LADSPA]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_DSSI, self.fSavedSettings[CARLA_KEY_PATHS_DSSI]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_LV2, self.fSavedSettings[CARLA_KEY_PATHS_LV2]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_VST2, self.fSavedSettings[CARLA_KEY_PATHS_VST2]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_VST3, self.fSavedSettings[CARLA_KEY_PATHS_VST3]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_SF2, self.fSavedSettings[CARLA_KEY_PATHS_SF2]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_SFZ, self.fSavedSettings[CARLA_KEY_PATHS_SFZ]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_JSFX, self.fSavedSettings[CARLA_KEY_PATHS_JSFX]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_CLAP, self.fSavedSettings[CARLA_KEY_PATHS_CLAP]
            )

        self._lastLoadedFromDialog = False
        ret = gCarla.felib.execPluginListDialog(self.fPluginListDialog)

        if not ret or getattr(self, "_lastLoadedFromDialog", False):
            return None

        if not self.host.is_engine_running():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Cannot add new plugins while engine is stopped"),
            )
            return

        btype = ret["build"]
        ptype = ret["type"]
        filename = ret["filename"]
        label = ret["label"]
        uniqueId = ret["uniqueId"]
        extraPtr = None

        return (btype, ptype, filename, label, uniqueId, extraPtr)

    def showAddJackAppDialog(self):
        ret = gCarla.felib.createAndExecJackAppDialog(
            self.fParentOrSelf, self.fProjectFilename
        )

        if not ret:
            return

        if not self.host.is_engine_running():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Cannot add new plugins while engine is stopped"),
            )
            return

        return ret

    @pyqtSlot()
    def slot_favoritePluginAdd(self):
        plugin = self.sender().data()

        if plugin is None:
            return

        self._preparePluginAddCanvasPos()
        if not self.host.add_plugin(
            plugin["build"],
            plugin["type"],
            plugin["filename"],
            None,
            plugin["label"],
            plugin["uniqueId"],
            None,
            PLUGIN_OPTIONS_NULL,
        ):
            # remove plugin from favorites
            try:
                self.fFavoritePlugins.remove(plugin)
            except ValueError:
                pass
            else:
                settingsDBf = QSafeSettings("falkTX", "CarlaDatabase2")
                settingsDBf.setValue("PluginDatabase/Favorites", self.fFavoritePlugins)
                settingsDBf.sync()
                del settingsDBf

            CustomMessageBox(
                self,
                QMessageBox.Icon.Critical,
                self.tr("Error"),
                self.tr("Failed to load plugin"),
                self.host.get_last_error(),
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )

    def slot_showPluginActionsMenu(self, sceneX=None, sceneY=None):
        if sceneX is not None and sceneY is not None and (sceneX != 0 or sceneY != 0):
            self._targetPluginAddPos = QPointF(float(sceneX), float(sceneY))
        else:
            self._targetPluginAddPos = None

        menu = QMenu(self)

        menu.addSection("Plugins")
        menu.addAction(self.ui.act_plugin_add)

        if len(self.fFavoritePlugins) != 0:
            fmenu = QMenu("Add from favorites", self)
            for p in self.fFavoritePlugins:
                act = fmenu.addAction(p["name"])
                act.setData(p)
                act.triggered.connect(self.slot_favoritePluginAdd)
            menu.addMenu(fmenu)

        menu.addAction(self.ui.act_plugin_remove_all)

        menu.addSection("All plugins (macros)")
        menu.addAction(self.ui.act_plugins_enable)
        menu.addAction(self.ui.act_plugins_disable)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_volume100)
        menu.addAction(self.ui.act_plugins_mute)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_wet100)
        menu.addAction(self.ui.act_plugins_bypass)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_center)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_compact)
        menu.addAction(self.ui.act_plugins_expand)
        menu.addSeparator()

        arrangeMenu = QMenu("Arrange & Align", menu)
        act_auto_arrange = arrangeMenu.addAction("Auto-arrange All")
        act_auto_arrange.triggered.connect(self.slot_canvasArrange)
        arrangeMenu.addSeparator()

        act_align_h = arrangeMenu.addAction("Align Horizontally")
        act_align_h.triggered.connect(lambda: self._alignSelectedCanvasNodes("align_h"))

        act_align_v = arrangeMenu.addAction("Align Vertically")
        act_align_v.triggered.connect(lambda: self._alignSelectedCanvasNodes("align_v"))

        act_dist_h = arrangeMenu.addAction("Distribute Horizontally")
        act_dist_h.triggered.connect(lambda: self._alignSelectedCanvasNodes("distribute_h"))

        act_dist_v = arrangeMenu.addAction("Distribute Vertically")
        act_dist_v.triggered.connect(lambda: self._alignSelectedCanvasNodes("distribute_v"))

        arrangeMenu.addSeparator()
        act_move_aside = arrangeMenu.addAction("Move Aside Non-Connected Nodes")
        act_move_aside.triggered.connect(self._moveAsideNonConnectedNodes)

        num_sel = len(self.scene.selectedItems()) if hasattr(self, "scene") and self.scene else 0
        if num_sel < 2:
            act_align_h.setEnabled(False)
            act_align_v.setEnabled(False)
            act_dist_h.setEnabled(False)
            act_dist_v.setEnabled(False)

        menu.addMenu(arrangeMenu)

        selectMenu = QMenu("Select", menu)
        act_sel_all = selectMenu.addAction("Select All\tCtrl+A")
        act_sel_all.triggered.connect(self._selectAllCanvasNodes)
        act_desel = selectMenu.addAction("Deselect\tCtrl+D")
        act_desel.triggered.connect(self._deselectAllCanvasNodes)
        act_inv = selectMenu.addAction("Invert Selection\tCtrl+Shift+I")
        act_inv.triggered.connect(self._invertCanvasSelection)
        selectMenu.addSeparator()

        from patchcanvas.patchcanvas import getAvailableNodeTypes, selectNodesByType
        byTypeMenu = QMenu("By Type", selectMenu)
        for t_name in getAvailableNodeTypes():
            act_t = byTypeMenu.addAction(t_name)
            act_t.triggered.connect(lambda checked=False, t=t_name: (selectNodesByType(t), self.updateMiniCanvasLater()))
        selectMenu.addMenu(byTypeMenu)

        menu.addMenu(selectMenu)

        menu.exec_(QCursor.pos())

    def _selectAllCanvasNodes(self):
        from patchcanvas.patchcanvas import selectAllNodes
        selectAllNodes()
        self.updateMiniCanvasLater()

    def _deselectAllCanvasNodes(self):
        from patchcanvas.patchcanvas import deselectAllNodes
        deselectAllNodes()
        self.updateMiniCanvasLater()

    def _invertCanvasSelection(self):
        from patchcanvas.patchcanvas import invertNodeSelection
        invertNodeSelection()
        self.updateMiniCanvasLater()

    def _alignSelectedCanvasNodes(self, mode):
        from patchcanvas.patchcanvas import alignSelected
        alignSelected(mode)
        self.updateMiniCanvasLater()

    def _moveAsideNonConnectedNodes(self):
        from patchcanvas.patchcanvas import moveAsideNonConnectedNodes
        moveAsideNonConnectedNodes()
        self.updateMiniCanvasLater()

    def startStartupPluginScanner(self):
        try:
            from pluginlist.startup_scanner import getGlobalScanner
            scanner = getGlobalScanner()
            paths = {
                PLUGIN_LADSPA: self.fSavedSettings.get(CARLA_KEY_PATHS_LADSPA, ""),
                PLUGIN_DSSI: self.fSavedSettings.get(CARLA_KEY_PATHS_DSSI, ""),
                PLUGIN_LV2: self.fSavedSettings.get(CARLA_KEY_PATHS_LV2, ""),
                PLUGIN_VST2: self.fSavedSettings.get(CARLA_KEY_PATHS_VST2, ""),
                PLUGIN_VST3: self.fSavedSettings.get(CARLA_KEY_PATHS_VST3, ""),
                PLUGIN_CLAP: self.fSavedSettings.get(CARLA_KEY_PATHS_CLAP, ""),
                PLUGIN_JSFX: self.fSavedSettings.get(CARLA_KEY_PATHS_JSFX, ""),
                PLUGIN_SF2: self.fSavedSettings.get(CARLA_KEY_PATHS_SF2, ""),
                PLUGIN_SFZ: self.fSavedSettings.get(CARLA_KEY_PATHS_SFZ, ""),
            }
            scanner.configure(paths=paths)
            scanner.start()
        except Exception as exc:
            log_carla(f"HostWindow: startStartupPluginScanner failed: {exc}", level="debug")

    def _preparePluginAddCanvasPos(self):
        try:
            if getattr(self, "_targetPluginAddPos", None) is not None:
                patchcanvas.setInitialPos(self._targetPluginAddPos.x(), self._targetPluginAddPos.y())
                self._targetPluginAddPos = None
            elif hasattr(self.ui, "graphicsView"):
                vp = self.ui.graphicsView.viewport()
                if vp:
                    center_scene = self.ui.graphicsView.mapToScene(vp.rect().center())
                    patchcanvas.setInitialPos(center_scene.x(), center_scene.y())
        except Exception:
            pass

    def loadPluginFromData(self, btype, ptype, filename, label, uniqueId, extraPtr, options=PLUGIN_OPTIONS_NULL):
        self._preparePluginAddCanvasPos()
        # Auto-sandbox plugins that create their own GL/UI context and crash the host when
        # loaded in-process (e.g. Cardinal/VCV Rack GLX races), unless the user explicitly
        # picked a bridge mode in the Add Plugin dialog.
        if not (options & (PLUGIN_OPTION_USE_BRIDGE | PLUGIN_OPTION_AVOID_BRIDGE)):
            ident = f"{label or ''} {filename or ''}".lower()
            if "cardinal" in ident or "decentsampler" in ident:
                options |= PLUGIN_OPTION_USE_BRIDGE
        cursor = getattr(Qt, "WaitCursor", None) or getattr(getattr(Qt, "CursorShape", object), "WaitCursor", None)
        if cursor is not None:
            QApplication.setOverrideCursor(cursor)
        try:
            ok = self.host.add_plugin(
                btype, ptype, filename, None, label, uniqueId, extraPtr, options
            )
        finally:
            if cursor is not None:
                QApplication.restoreOverrideCursor()

        if not ok:
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Failed to load plugin"),
                self.host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return False
        return True

