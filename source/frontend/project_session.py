#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import time
from datetime import datetime
from qt_compat import QTimer
from project_storage import storage_manager
from carla_shared import log_carla

class ProjectSessionManager:
    """
    Manages session lifecycle:
      - Periodic and on-demand autosaving to a dedicated project autosave directory
      - Max autosave rotation
      - Automatic pruning of autosaves on clean manual save
      - Fast on-move autosave position sync
      - Crash / recovery detection on startup or project open
    """
    def __init__(self, host_window):
        self.host_window = host_window
        self.enabled = True
        self.interval_minutes = 3
        self.max_autosaves = 5

        # Timing tracking
        self.last_autosave_time = None
        self._next_autosave_timestamp = None

        # Background timer (checks every 1 sec for countdown accuracy)
        self._tick_timer = QTimer()
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)

        # Debounce timer for updating node positions on move
        self._pos_debounce_timer = QTimer()
        self._pos_debounce_timer.setSingleShot(True)
        self._pos_debounce_timer.setInterval(400)
        self._pos_debounce_timer.timeout.connect(self._sync_latest_autosave_positions)

        self._last_autosave_file = None

    def start(self, interval_minutes=None, max_autosaves=None, enabled=True):
        self.enabled = enabled
        if interval_minutes is not None:
            self.interval_minutes = max(1, int(interval_minutes))
        if max_autosaves is not None:
            self.max_autosaves = max(1, int(max_autosaves))

        self._tick_timer.stop()
        if self.enabled:
            self._next_autosave_timestamp = time.time() + (self.interval_minutes * 60)
            self._tick_timer.start()

    def stop(self):
        self._tick_timer.stop()
        self._pos_debounce_timer.stop()

    def get_seconds_until_next_autosave(self):
        if not self.enabled or self._next_autosave_timestamp is None:
            return None
        return max(0, int(self._next_autosave_timestamp - time.time()))

    @staticmethod
    def get_canonical_project_filepath(project_filepath):
        if not project_filepath:
            return ""
        abs_path = os.path.abspath(project_filepath)
        if ".autosaves" in abs_path:
            parts = abs_path.split(os.sep)
            idx = parts.index(".autosaves")
            dir_path = os.sep.join(parts[:idx])
            filename = os.path.basename(abs_path)
            base, ext = os.path.splitext(filename)
            import re
            base = re.sub(r"_auto_\d{8}_\d{6}", "", base)
            while base.endswith("_auto"):
                base = base[:-5]
            return os.path.join(dir_path, base + ext)
        return abs_path

    def get_autosave_dir(self, project_filepath):
        if not project_filepath:
            return None
        canonical = self.get_canonical_project_filepath(project_filepath)
        project_dir = os.path.dirname(canonical)
        base_name = os.path.splitext(os.path.basename(canonical))[0]
        autosave_dir = os.path.join(project_dir, ".autosaves", base_name)
        return autosave_dir

    def get_available_autosaves(self, project_filepath):
        autosave_dir = self.get_autosave_dir(project_filepath)
        if not autosave_dir or not os.path.exists(autosave_dir):
            return []

        files = []
        for f in os.listdir(autosave_dir):
            full_path = os.path.join(autosave_dir, f)
            if storage_manager.is_project_file(full_path):
                files.append(full_path)

        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files

    def check_newer_autosave(self, project_filepath):
        """Returns the most recent autosave if it is strictly newer than the main file"""
        if not project_filepath or not os.path.exists(project_filepath):
            return None
        autosaves = self.get_available_autosaves(project_filepath)
        if not autosaves:
            return None

        latest_autosave = autosaves[0]
        try:
            main_mtime = os.path.getmtime(project_filepath)
            auto_mtime = os.path.getmtime(latest_autosave)
            if auto_mtime > main_mtime + 2.0:
                return latest_autosave
        except Exception:
            pass
        return None

    def create_autosave(self, is_scheduled=True):
        if not self.enabled:
            return None
        if not self.host_window.fProjectFilename:
            return None
        if not self.host_window.host.is_engine_running():
            return None

        # If scheduled periodic autosave, only save if changes exist
        if is_scheduled and not getattr(self.host_window, "fHasUnsavedChanges", False):
            return None

        project_filepath = self.host_window.fProjectFilename
        autosave_dir = self.get_autosave_dir(project_filepath)
        if not autosave_dir:
            return None

        try:
            canonical_path = self.get_canonical_project_filepath(project_filepath)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(canonical_path)[1] or storage_manager.default_extension()
            base_name = os.path.splitext(os.path.basename(canonical_path))[0]
            autosave_file = os.path.join(autosave_dir, f"{base_name}_auto_{timestamp}{ext}")

            # 1. Ask Carla backend engine to save state (it writes the project format directly)
            backend_target, is_temp = storage_manager.prepare_for_backend_save(autosave_file)

            if not self.host_window.host.save_project(backend_target):
                return None

            # 2. Add the frontend-only canvas positions
            from patchcanvas import patchcanvas
            positions = patchcanvas.saveGroupPositions() if getattr(self.host_window, "fWithCanvas", False) else []

            if storage_manager.finalize_from_backend_save(autosave_file, backend_target, positions) is False:
                return None

            self._last_autosave_file = autosave_file
            self.last_autosave_time = datetime.now()
            self._next_autosave_timestamp = time.time() + (self.interval_minutes * 60)

            # 3. Prune old autosaves to enforce max retention
            self._prune_autosaves(autosave_dir)
            return autosave_file
        except Exception as e:
            log_carla(f"ProjectSessionManager::create_autosave failed: {e}", level="warn")
            return None

    def queue_node_position_sync(self):
        """Called whenever a patchbay node moves to keep the latest autosave updated"""
        if not self.enabled or not self.host_window.fProjectFilename:
            return
        self._pos_debounce_timer.start()

    def _sync_latest_autosave_positions(self):
        autosaves = self.get_available_autosaves(self.host_window.fProjectFilename)
        target_file = self._last_autosave_file if (self._last_autosave_file and os.path.exists(self._last_autosave_file)) else (autosaves[0] if autosaves else None)

        if target_file and os.path.exists(target_file):
            try:
                from patchcanvas import patchcanvas
                positions = patchcanvas.saveGroupPositions()
                storage_manager.save_canvas_positions(target_file, positions)
            except Exception as e:
                log_carla(f"ProjectSessionManager::_sync_latest_autosave_positions failed: {e}", level="debug")
        else:
            # If no autosave exists yet, create one now
            self.create_autosave(is_scheduled=False)

    def prune_all_autosaves_on_manual_save(self, project_filepath):
        """Delete the autosaves this session wrote, never another running instance's files."""
        autosave_dir = self.get_autosave_dir(project_filepath)
        if not autosave_dir or not os.path.exists(autosave_dir):
            return
        try:
            if self._last_autosave_file and os.path.exists(self._last_autosave_file):
                os.remove(self._last_autosave_file)
            try:
                os.rmdir(autosave_dir)  # only succeeds when no other instance left files there
            except OSError:
                pass
            self._last_autosave_file = None
            self.last_autosave_time = None
        except Exception as e:
            log_carla(f"ProjectSessionManager::prune_all_autosaves failed: {e}", level="debug")

    def _prune_autosaves(self, autosave_dir):
        if not os.path.exists(autosave_dir):
            return
        autosaves = []
        for f in os.listdir(autosave_dir):
            p = os.path.join(autosave_dir, f)
            if storage_manager.is_project_file(p):
                autosaves.append(p)

        if len(autosaves) > self.max_autosaves:
            autosaves.sort(key=lambda p: os.path.getmtime(p))
            to_remove = autosaves[: len(autosaves) - self.max_autosaves]
            for p in to_remove:
                try:
                    os.remove(p)
                except Exception:
                    pass

    def _on_tick(self):
        if not self.enabled:
            return
        now = time.time()
        if self._next_autosave_timestamp and now >= self._next_autosave_timestamp:
            self._next_autosave_timestamp = now + (self.interval_minutes * 60)
            self.create_autosave(is_scheduled=True)
