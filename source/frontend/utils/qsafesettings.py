#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import QSettings

# ---------------------------------------------------------------------------------------------------------------------
# Safer QSettings class, which does not throw if type mismatches

class QSafeSettings(QSettings):
    def value(self, key, defaultValue, valueType):
        if not isinstance(defaultValue, valueType):
            print("QSafeSettings.value() - defaultValue type mismatch for key", key)

        try:
            return QSettings.value(self, key, defaultValue, valueType)
        except Exception:
            return defaultValue

# ---------------------------------------------------------------------------------------------------------------------
