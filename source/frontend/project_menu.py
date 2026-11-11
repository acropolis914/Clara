#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Recent-project bookkeeping and the File menu actions, split out of host_app.py.
# HostWindow inherits this mixin.

import os
from datetime import datetime

from carla_app import QSafeSettings, gCarla
from carla_shared import CARLA_KEY_MAIN_PROJECT_FOLDER, CustomMessageBox
from carla_widgets import ProjectSessionOfferDialog
from project_storage import storage_manager
from qt_compat import QAction, QFileDialog, QMessageBox, QTimer, pyqtSlot


class ProjectMenuMixin:
    # --------------------------------------------------------------------------------------------------------
    # Recent Projects

    def addRecentProject(self, filename):
        if not filename or not storage_manager.is_project_file(filename):
            return
        absPath = os.path.abspath(filename)
        if absPath in self.fRecentProjects:
            self.fRecentProjects.remove(absPath)
        self.fRecentProjects.insert(0, absPath)
        self.fRecentProjects = self.fRecentProjects[:10]
        self.updateRecentProjectsMenu()

    def updateRecentProjectsMenu(self):
        for act in self.fRecentProjectActions:
            self.ui.menu_File.removeAction(act)
        self.fRecentProjectActions = []

        valid_recents = [f for f in self.fRecentProjects if os.path.exists(f)]
        if not valid_recents:
            return

        for path in valid_recents:
            act = QAction(os.path.basename(path), self)
            act.setToolTip(path)
            act.setStatusTip(path)
            act.triggered.connect(
                lambda checked=False, p=path: self.loadRecentProject(p)
            )
            self.ui.menu_File.insertAction(self.ui.act_file_save, act)
            self.fRecentProjectActions.append(act)

        sep = self.ui.menu_File.insertSeparator(self.ui.act_file_save)
        self.fRecentProjectActions.append(sep)

    def loadRecentProject(self, filename):
        if not os.path.exists(filename):
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("File does not exist"),
                filename,
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return

        if self.fPluginCount > 0:
            ask = QMessageBox.question(
                self,
                self.tr("Question"),
                self.tr(
                    "There are some plugins loaded, do you want to remove them now?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ask != QMessageBox.Yes:
                return

        # Check for newer autosave recovery
        if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
            newer_autosave = self.fSessionManager.check_newer_autosave(filename)
            if newer_autosave:
                mtime_str = datetime.fromtimestamp(os.path.getmtime(newer_autosave)).strftime("%Y-%m-%d %H:%M:%S")
                rec_ask = QMessageBox.question(
                    self,
                    self.tr("Autosave Recovery Detected"),
                    self.tr(
                        f"A newer autosave exists from {mtime_str} for this project.\n\nWould you like to recover the autosaved session instead?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if rec_ask == QMessageBox.Yes:
                    filename = newer_autosave

        self.pluginRemoveAll()
        self.loadProjectLater(filename)

    def checkRecentOnStartup(self):
        if self.fProjectFilename or self.host.isControl or self.host.isPlugin:
            if not self.host.isControl:
                self.slot_engineStart()
            return

        recent_file = None
        for path in self.fRecentProjects:
            if os.path.exists(path):
                recent_file = path
                break

        if recent_file:
            recovery_source = None
            recovery_mtime = None
            if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
                newer_autosave = self.fSessionManager.check_newer_autosave(recent_file)
                if newer_autosave:
                    recovery_source = newer_autosave
                    try:
                        recovery_mtime = os.path.getmtime(newer_autosave)
                    except OSError:
                        recovery_mtime = None

            is_autoload = getattr(gCarla, "autoload_lastsave", False) or QSafeSettings().value("Main/AutoloadLastSave", False, bool)
            if is_autoload:
                self.loadProjectLater(recent_file, source_override=recovery_source)
                return

            def _on_recent_load():
                # Recovered autosaves are loaded as the last-saved project: content comes from
                # the autosave, but the name/path stays the real project so saving writes there.
                self.loadProjectLater(recent_file, source_override=recovery_source)

            def _on_recent_skip():
                self.fLoadingDialog = None
                if not self.host.isControl:
                    self.slot_engineStart()
                    if self.fWithCanvas:
                        QTimer.singleShot(600, self.slot_canvasArrange)

            offer_detail = None
            if recovery_source:
                if recovery_mtime is not None:
                    mtime_str = datetime.fromtimestamp(recovery_mtime).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    mtime_str = self.tr("an unknown time")
                offer_detail = self.tr(
                    f"A newer autosave from {mtime_str} was found for this project.\n\n"
                    f"Recovering restores the autosaved session but keeps the last-saved name and path "
                    f"('{os.path.basename(recent_file)}')."
                )

            self.fLoadingDialog = ProjectSessionOfferDialog(
                self.fParentOrSelf,
                recent_file,
                offer_mode=True,
                recover_mode=bool(recovery_source),
                offer_detail=offer_detail,
                on_load_accepted=_on_recent_load,
                on_load_declined=_on_recent_skip,
            )
            self.fLoadingDialog.show()
            return

        # Not loading recent: start engine and auto-arrange canvas
        if not self.host.isControl:
            self.slot_engineStart()
            if self.fWithCanvas:
                QTimer.singleShot(600, self.slot_canvasArrange)

    # --------------------------------------------------------------------------------------------------------
    # Files (menu actions)

    @pyqtSlot()
    def slot_fileNew(self):
        if (
            self.fPluginCount > 0
            and QMessageBox.question(
                self,
                self.tr("New File"),
                self.tr(
                    "Plugins that are currently loaded will be removed. Are you sure?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.No
        ):
            return

        self.pluginRemoveAll()
        self.fProjectFilename = ""
        self.setProperWindowTitle()
        self.host.clear_project_filename()

    @pyqtSlot()
    def slot_fileOpen(self):
        fileFilter = storage_manager.open_filter()
        filename, ok = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Carla Project File"),
            self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER],
            filter=fileFilter,
        )

        if not filename:
            return

        # Check for newer autosave recovery
        load_source = filename
        if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
            newer_autosave = self.fSessionManager.check_newer_autosave(filename)
            if newer_autosave:
                mtime_str = datetime.fromtimestamp(os.path.getmtime(newer_autosave)).strftime("%Y-%m-%d %H:%M:%S")
                rec_ask = QMessageBox.question(
                    self,
                    self.tr("Autosave Recovery Detected"),
                    self.tr(
                        f"A newer autosave exists from {mtime_str} for this project.\n\nWould you like to recover the autosaved session instead?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if rec_ask == QMessageBox.Yes:
                    load_source = newer_autosave

        newFile = True

        if self.fPluginCount > 0:
            ask = QMessageBox.question(
                self,
                self.tr("Question"),
                self.tr(
                    "There are some plugins loaded, do you want to remove them now?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            newFile = ask == QMessageBox.Yes

        if newFile:
            self.pluginRemoveAll()
            self.fProjectFilename = filename
            self.setProperWindowTitle()
            if not self.loadProjectNow(source_override=load_source):
                # Rack is already empty and the new file did not load: start clean rather than
                # keeping a filename that cannot be read (a later save would overwrite it).
                self.fProjectFilename = ""
                self.setProperWindowTitle()
        else:
            filenameOld = self.fProjectFilename
            self.fProjectFilename = filename
            self.loadProjectNow(source_override=load_source)
            self.fProjectFilename = filenameOld

    @pyqtSlot()
    def slot_fileSave(self, *args, **kwargs):
        saveAs = kwargs.get("saveAs", False)
        if self.fProjectFilename and not saveAs:
            return self.saveProjectNow()

        fileFilter = storage_manager.save_filter()
        selected_filter = ""
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Carla Project File"),
            self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER],
            filter=fileFilter,
        )

        if not filename:
            return

        # The chosen format travels as a tag; the save manager alone decides the extension.
        chosen_tag = storage_manager.tag_from_filter(selected_filter)
        filename = storage_manager.ensure_extension(filename, tag=chosen_tag)

        if self.fProjectFilename != filename:
            self.fProjectFilename = filename
            self.setProperWindowTitle()

        self.saveProjectNow()
        self.ui.act_file_save.setEnabled(True)

    @pyqtSlot()
    def slot_fileSaveAs(self, *args, **kwargs):
        self.slot_fileSave(saveAs=True)

    @pyqtSlot()
    def slot_loadProjectNow(self):
        source_override = getattr(self, "fProjectSourceOverride", None)
        self.fProjectSourceOverride = None
        if not self.loadProjectNow(source_override=source_override):
            # Keep the app honest about an empty session instead of saving over the unreadable file.
            self.fProjectFilename = ""
            self.setProperWindowTitle()
        if self.fProjectFilename and os.path.exists(self.fProjectFilename):
            self.ui.act_file_save.setEnabled(True)

