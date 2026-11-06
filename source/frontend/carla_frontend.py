#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Carla frontend dialogs - pure PyQt6 implementation.
#
# Historically the About / Jack-Application / Plugin-List dialogs lived in a separate
# Qt-linked native library (libcarla_frontend). That forced the host to ship a Qt build
# matching the native one, which conflicted with PyQt6's bundled Qt. These dialogs are now
# implemented in Python; the only native code used is the (non-Qt) libcarla_utils backend
# for plugin discovery.
#
# The class below keeps the same public API as the old ctypes wrapper so that
# host_app.py does not need to change.

# ---------------------------------------------------------------------------------------------------------------------
# Imports (ctypes)

from ctypes import (
    c_bool, c_char, c_char_p, c_uint, c_uint64, Structure
)

# ---------------------------------------------------------------------------------------------------------------------
# Result structures (kept for API/source compatibility with the old native library)

class JackApplicationDialogResults(Structure):
    _fields_ = [
        ("command", c_char_p),
        ("name", c_char_p),
        ("labelSetup", c_char_p)
    ]

class HostSettings(Structure):
    _fields_ = [
        ("showPluginBridges", c_bool),
        ("showWineBridges", c_bool),
        ("useSystemIcons", c_bool),
        ("wineAutoPrefix", c_bool),
        ("wineExecutable", c_char_p),
        ("wineFallbackPrefix", c_char_p),
    ]

class PluginListDialogResults(Structure):
    _fields_ = [
        ("build", c_uint),
        ("type", c_uint),
        ("hints", c_uint),
        ("category", c_char_p),
        ("filename", c_char_p),
        ("name", c_char_p),
        ("label", c_char_p),
        ("maker", c_char_p),
        ("uniqueId", c_uint64),
        ("audioIns", c_uint),
        ("audioOuts", c_uint),
        ("cvIns", c_uint),
        ("cvOuts", c_uint),
        ("midiIns", c_uint),
        ("midiOuts", c_uint),
        ("parametersIns", c_uint),
        ("parametersOuts", c_uint),
    ]

# ---------------------------------------------------------------------------------------------------------------------
# Carla Frontend object (pure Python)

class CarlaFrontendLib():
    def __init__(self, filename=None):
        # No native library is loaded anymore; kept for API compatibility.
        self.lib = None
        self.filename = filename

    # --------------------------------------------------------------------------------------------------------

    def createAndExecAboutDialog(self, parent, hostHandle, isControl, isPlugin):
        from dialogs.aboutdialog_py import createAndExecAboutDialog
        return createAndExecAboutDialog(parent, hostHandle, isControl, isPlugin)

    def createAndExecJackAppDialog(self, parent, projectFilename):
        from dialogs.jackappdialog_py import createAndExecJackAppDialog
        return createAndExecJackAppDialog(parent, projectFilename)

    def createPluginListDialog(self, parent, hostSettings):
        from pluginlist.pluginlistdialog_py import createPluginListDialog
        return createPluginListDialog(parent, hostSettings)

    def destroyPluginListDialog(self, dialog):
        from pluginlist.pluginlistdialog_py import destroyPluginListDialog
        return destroyPluginListDialog(dialog)

    def setPluginListDialogPath(self, dialog, ptype, path):
        from pluginlist.pluginlistdialog_py import setPluginListDialogPath
        return setPluginListDialogPath(dialog, ptype, path)

    def execPluginListDialog(self, dialog):
        from pluginlist.pluginlistdialog_py import execPluginListDialog
        return execPluginListDialog(dialog)

    def getCachedPluginsCsv(self, dialog):
        from pluginlist.pluginlistdialog_py import getCachedPluginsCsv
        return getCachedPluginsCsv(dialog)

# ------------------------------------------------------------------------------------------------------------
