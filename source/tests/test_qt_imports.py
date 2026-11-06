#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Qt names moved to qt_compat must still exist where the modules use them.

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from qt_compat import QApplication

app = QApplication.instance() or QApplication([])


def test_pluginlist_qt_names():
    from pluginlist import pluginlistdialog_py as dialog

    for name in ("QComboBox", "QByteArray", "QListView", "QRadioButton", "QToolBox"):
        assert hasattr(dialog, name), f"pluginlistdialog_py is missing {name}"


def test_qtweb_backend_names():
    import carla_backend_qtweb as backend

    for name in ("ENGINE_CALLBACK_QUIT", "PyCarlaTransportInfo"):
        assert hasattr(backend, name), f"carla_backend_qtweb is missing {name}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("qt_imports: all checks passed")
