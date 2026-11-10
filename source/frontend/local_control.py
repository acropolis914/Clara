#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Local control-channel handlers (claramsg) and control-driven project open,
# split out of host_app.py. HostWindow inherits this mixin.

import os

from qt_compat import QMessageBox, QTimer

from carla_logger import logger, LEVEL_NAMES
from carla_shared import log_carla


class ControlMixin:
    def msgEvents(self, count=50, tag=None, level=None):
        try:
            count = max(1, min(int(count), 2000))
        except (TypeError, ValueError):
            count = 50
        history = list(logger.history)
        if tag:
            tag = str(tag).upper()
            history = [entry for entry in history if tag in entry.tag]
        if level:
            level = str(level).upper()
            history = [entry for entry in history
                       if LEVEL_NAMES.get(entry.level, "INFO").upper() == level]
        else:
            history = [entry for entry in history
                       if LEVEL_NAMES.get(entry.level, "INFO").upper() != "DEBUG"]
        history = history[-count:]
        return [
            {
                "time": entry.timestamp.strftime("%H:%M:%S"),
                "level": LEVEL_NAMES.get(entry.level, "INFO"),
                "tag": entry.tag,
                "message": entry.message,
            }
            for entry in history
        ]

    def msgScreenshot(self, path=None, dialog=False):
        try:
            from qt_compat import QApplication
            target = self
            if dialog:
                target = QApplication.activeModalWidget() or QApplication.activeWindow() or self
            import tempfile
            if path is None:
                # mkstemp gives a private 0600 regular file, so a predictable /tmp path
                # cannot be pre-created as a symlink to a victim file.
                fd, path = tempfile.mkstemp(prefix="clara-screenshot-", suffix=".png",
                                            dir=tempfile.gettempdir())
                os.close(fd)
            else:
                path = os.path.abspath(os.path.expanduser(str(path)))
                if os.path.islink(path) or (os.path.exists(path) and not os.path.isfile(path)):
                    return {"ok": False, "error": "refusing to overwrite a symlink or special file"}
                folder = os.path.dirname(path)
                if folder:
                    os.makedirs(folder, exist_ok=True)
            pixmap = target.grab()
            if target is self:
                view = getattr(self.ui, "graphicsView", None)
                if view is not None and view.isVisible():
                    try:
                        from qt_compat import QImage, QPainter, QPoint, QRect, QRectF, Qt
                        size = view.viewport().size()
                        dpr = view.devicePixelRatioF() or 1.0
                        image_format = getattr(QImage, "Format_ARGB32_Premultiplied", None)
                        if image_format is None:
                            image_format = QImage.Format.Format_ARGB32_Premultiplied
                        image = QImage(int(size.width() * dpr), int(size.height() * dpr),
                                       image_format)
                        image.setDevicePixelRatio(dpr)
                        scene = view.scene()
                        brush = scene.backgroundBrush() if scene is not None else None
                        if brush is not None and brush.style() != Qt.NoBrush:
                            image.fill(brush.color())
                        else:
                            image.fill(view.palette().window().color())
                        painter = QPainter(image)
                        try:
                            # Render the scene, not the GL framebuffer: grab() and
                            # grabFramebuffer() miss the GL viewport, but the scene
                            # renderer paints the same nodes and cables.
                            view.render(painter, QRectF(0.0, 0.0, float(size.width()), float(size.height())), view.viewport().rect())
                        finally:
                            painter.end()
                        pos = view.viewport().mapTo(self, QPoint(0, 0))
                        log_carla(
                            f"msgScreenshot: view_visible={view.isVisible()} "
                            f"viewport={size.width()}x{size.height()} "
                            f"scene_items={len(scene.items()) if scene is not None else 0} "
                            f"image={image.width()}x{image.height()} null={image.isNull()} pos={pos.x()},{pos.y()}",
                            level="debug",
                        )
                        painter = QPainter(pixmap)
                        painter.drawImage(pos, image)
                        painter.end()
                        overlays = [getattr(getattr(self, "canvasFilter", None), "toolBar", None),
                                    getattr(getattr(self, "canvasFilter", None), "contextToolBar", None),
                                    getattr(view, "fSearchList", None)]
                        for overlay in overlays:
                            if overlay is None or not overlay.isVisible():
                                continue
                            p = overlay.mapTo(self, QPoint(0, 0))
                            painter = QPainter(pixmap)
                            painter.drawPixmap(p, overlay.grab())
                            painter.end()
                    except Exception as exc:
                        log_carla(f"msgScreenshot: canvas composite failed: {exc}", level="warn")
            if pixmap is None or not pixmap.save(path, "PNG"):
                return {"ok": False, "error": "could not save screenshot"}
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            return {"ok": True, "path": path, "width": pixmap.width(), "height": pixmap.height()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def msgDialogs(self):
        try:
            from qt_compat import QApplication, QDialog, QPushButton
            result = []
            for widget in QApplication.topLevelWidgets():
                if not isinstance(widget, QDialog) or not widget.isVisible():
                    continue
                buttons = []
                try:
                    for button in widget.findChildren(QPushButton):
                        if button.isVisible() and button.text():
                            buttons.append(button.text())
                except Exception:
                    pass
                result.append({
                    "title": widget.windowTitle(),
                    "modal": bool(widget.isModal()),
                    "buttons": buttons,
                })
            return {"ok": True, "dialogs": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def msgDialogAction(self, action, text=None, force=False):
        try:
            from qt_compat import QApplication, QDialog, QPushButton
            target = QApplication.activeModalWidget() or QApplication.activeWindow()
            if not isinstance(target, QDialog):
                return {"ok": False, "error": "no active dialog"}
            title = target.windowTitle()
            if action == "accept":
                target.accept()
                log_carla("claramsg: accepted dialog '%s'" % title)
                return {"ok": True, "accepted": title}
            if action == "cancel":
                target.reject()
                log_carla("claramsg: cancelled dialog '%s'" % title)
                return {"ok": True, "cancelled": title}
            if action == "click":
                if not text:
                    return {"ok": False, "error": "click needs a button text"}
                wanted = str(text).casefold()
                dangerous = ("discard", "delete", "remove", "erase", "overwrite", "format", "reset", "quit")
                if not force and any(word in wanted for word in dangerous):
                    return {"ok": False, "error": "refusing destructive button without force"}
                for button in target.findChildren(QPushButton):
                    if button.isVisible() and wanted in (button.text() or "").casefold():
                        QTimer.singleShot(0, button.click)
                        log_carla("claramsg: clicked '%s' on dialog '%s'" % (button.text(), title))
                        return {"ok": True, "clicked": button.text(), "title": title}
                return {"ok": False, "error": "no matching button"}
            return {"ok": False, "error": "unknown dialog action: %s" % action}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # --------------------------------------------------------------------------------------------------------
    # Settings dialog control (claramsg settings ...)

    def _findSettingsDialog(self):
        try:
            from qt_compat import QApplication
            from carla_settings import CarlaSettingsW
        except Exception:
            return None
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, CarlaSettingsW) and widget.isVisible():
                return widget
        return None

    @staticmethod
    def _settingsPages(dialog):
        """Return [(row, name, hidden)] for the settings page list."""
        rows = dialog.ui.lw_page
        pages = []
        for row in range(rows.rowCount()):
            item = rows.item(row, 0)
            pages.append((row, item.text() if item is not None else "", rows.isRowHidden(row)))
        return pages

    def _settingsField(self, dialog, field_id):
        """Return (builder, widget) for a schema field id, or (None, None)."""
        builders = []
        for row, _name, _hidden in self._settingsPages(dialog):
            # A page only gets its builder once built; set/get must work on any page.
            dialog._ensure_tab_built(row)
            builder = dialog.form_builder_for_row(row)
            if builder is not None:
                builders.append(builder)
        for builder in builders:
            widget = builder.widgets.get(field_id)
            if widget is not None:
                return builder, widget
        return None, None

    @staticmethod
    def _settingsValue(widget):
        from qt_compat import QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSlider, QSpinBox
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QSlider):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QSpinBox):
            return widget.value()
        return None

    @classmethod
    def _setSettingsValue(cls, widget, raw):
        from qt_compat import QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSlider, QSpinBox
        if isinstance(widget, QCheckBox):
            value = str(raw).strip().lower() in ("1", "true", "on", "yes", "checked")
            widget.setChecked(value)
            return value
        if isinstance(widget, QComboBox):
            index = widget.findText(str(raw))
            if index < 0:
                index = widget.findData(raw)
            if index < 0:
                raise ValueError("no such option: %s" % raw)
            widget.setCurrentIndex(index)
            return widget.currentText()
        if isinstance(widget, QSlider):
            widget.setValue(int(round(float(raw))))
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(raw))
            return widget.value()
        if isinstance(widget, QSpinBox):
            widget.setValue(int(round(float(raw))))
            return widget.value()
        if isinstance(widget, QLineEdit):
            widget.setText(str(raw))
            return widget.text()
        raise ValueError("unsupported field type")

    def _settingsPageNames(self, dialog):
        return [name for _row, name, _hidden in self._settingsPages(dialog)]

    def msgSettings(self, action, target=None, value=None, force=False):
        try:
            dialog = self._findSettingsDialog()
            if action == "open":
                if dialog is not None:
                    return {"ok": True, "already_open": True}
                # slot_configureCarla() runs a modal loop; defer it so this reply
                # is sent before the dialog takes over the event loop.
                QTimer.singleShot(0, self.slot_configureCarla)
                return {"ok": True}
            if dialog is None:
                return {"ok": False, "error": "settings dialog is not open"}
            if action == "close":
                dialog.reject()
                return {"ok": True, "closed": True}
            if action == "apply":
                dialog.slot_applySettings()
                return {"ok": True, "applied": True}
            if action == "reset":
                if not force:
                    return {"ok": False, "error": "refusing to reset settings without force"}
                dialog.slot_resetSettings()
                return {"ok": True, "reset": True}
            if action == "pages":
                return {"ok": True, "pages": [
                    {"row": row, "name": name, "hidden": hidden}
                    for row, name, hidden in self._settingsPages(dialog)]}
            if action == "page":
                if not target:
                    return {"ok": False, "error": "page needs a name",
                            "pages": self._settingsPageNames(dialog)}
                wanted = str(target).casefold()
                for row, name, _hidden in self._settingsPages(dialog):
                    if name.casefold() == wanted:
                        dialog.ui.lw_page.setCurrentCell(row, 0)
                        dialog.ui.lw_page.selectRow(row)
                        dialog._ensure_tab_built(row)
                        return {"ok": True, "page": name, "row": row}
                return {"ok": False, "error": "no such page: %s" % target,
                        "pages": self._settingsPageNames(dialog)}
            if action == "fields":
                fields = []
                wanted = str(target).casefold() if target else None
                for row, name, _hidden in self._settingsPages(dialog):
                    if wanted is not None and name.casefold() != wanted:
                        continue
                    dialog._ensure_tab_built(row)
                    builder = dialog.form_builder_for_row(row)
                    if builder is None:
                        continue
                    for field_id, fdef in builder.field_defs.items():
                        widget = builder.widgets.get(field_id)
                        if widget is None:
                            continue
                        fields.append({"id": field_id, "type": fdef.get("type"),
                                       "page": name, "value": self._settingsValue(widget)})
                return {"ok": True, "fields": fields}
            if action in ("get", "set"):
                if not target:
                    return {"ok": False, "error": "%s needs a field id" % action}
                builder, widget = self._settingsField(dialog, target)
                if widget is None:
                    return {"ok": False, "error": "no such field: %s" % target}
                if action == "get":
                    return {"ok": True, "field": target, "value": self._settingsValue(widget)}
                if value is None:
                    return {"ok": False, "error": "set needs a value"}
                try:
                    new_value = self._setSettingsValue(widget, value)
                except (TypeError, ValueError) as exc:
                    return {"ok": False, "error": str(exc)}
                return {"ok": True, "field": target, "value": new_value}
            return {"ok": False, "error": "unknown settings action: %s" % action}
        except Exception as exc:
            import traceback
            log_carla("claramsg settings error: %s" % traceback.format_exc(), level="warn")
            return {"ok": False, "error": str(exc)}

    # --------------------------------------------------------------------------------------------------------
    # Canvas control (claramsg canvas ...)

    def msgCanvas(self, action, value=None):
        scene = getattr(self, "scene", None)
        if scene is None:
            return {"ok": False, "error": "no canvas"}
        try:
            if action == "zoom":
                if value is None:
                    return {"ok": False, "error": "zoom needs a scale or in/out/fit/reset"}
                text = str(value).strip().lower()
                if text == "in":
                    scene.zoom_in()
                elif text == "out":
                    scene.zoom_out()
                elif text == "fit":
                    scene.zoom_fit()
                elif text == "reset":
                    scene.zoom_reset()
                else:
                    scale = max(scene.m_scale_min, min(scene.m_scale_max, float(text)))
                    view = scene.getView()
                    transform = view.transform()
                    transform.reset()
                    transform.scale(scale, scale)
                    view.setTransform(transform)
                    scene.scaleChanged.emit(scale)
                return {"ok": True, "scale": round(scene.getScaleFactor(), 4)}
            if action == "select":
                import patchcanvas
                scene = patchcanvas.canvas.scene
                if scene is None:
                    return {"ok": False, "error": "no canvas scene"}
                text = str(value or "none").strip().lower()
                if text in ("none", "clear", ""):
                    scene.clearSelection()
                elif text == "all":
                    for group in getattr(patchcanvas.canvas, "group_list", []):
                        for widget in getattr(group, "widgets", []):
                            if widget is not None:
                                widget.setSelected(True)
                else:
                    wanted = set()
                    for part in text.replace(" ", ",").split(","):
                        if part.isdigit():
                            wanted.add(int(part))
                    for group in getattr(patchcanvas.canvas, "group_list", []):
                        for widget in getattr(group, "widgets", []):
                            if widget is not None:
                                widget.setSelected(group.group_id in wanted)
                return {"ok": True, "selected": len(scene.selectedItems())}
            if action == "state":
                import patchcanvas
                data = {
                    "scale": round(scene.getScaleFactor(), 4),
                    "nodes": len(getattr(patchcanvas.canvas, "group_list", [])),
                    "connections": len(getattr(patchcanvas.canvas, "connection_list", [])),
                    "containers": len(getattr(patchcanvas.canvas, "container_list", [])),
                }
                options = patchcanvas.options
                for key in ("box_shadows", "shadow_spread", "shadow_distance",
                            "shadow_opacity", "shadow_dragging"):
                    data[key] = getattr(options, key, None)
                theme = getattr(patchcanvas.canvas, "theme", None)
                if theme is not None:
                    for key in ("box_text", "box_text_sel", "box_pen", "box_bg_1", "canvas_bg"):
                        value = getattr(theme, key, None)
                        if hasattr(value, "color"):
                            value = value.color()
                        data[key] = value.name() if hasattr(value, "name") else None
                return {"ok": True, "canvas": data}
            return {"ok": False, "error": "unknown canvas action: %s" % action}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def msgPlugin(self, action, plugin_id=None, value=None):
        if action != "ui":
            return {"ok": False, "error": "unknown plugin action: %s" % action}
        try:
            pid = int(plugin_id)
        except (TypeError, ValueError):
            return {"ok": False, "error": "plugin id must be an integer"}
        if pid < 0 or pid >= int(getattr(self, "fPluginCount", 0)):
            return {"ok": False, "error": "no such plugin: %s" % plugin_id}
        show = True if value is None else str(value).lower() not in ("0", "off", "false", "hide")
        self.host.show_custom_ui(pid, show)
        return {"ok": True, "plugin": pid, "shown": show,
                "name": self.host.get_plugin_info(pid)["name"]}

    def msgQuit(self, force=False):
        """Close the window through the normal path; refuse to lose unsaved edits."""
        if getattr(self, "fHasUnsavedChanges", False) and not force:
            return {"ok": False, "error": "unsaved changes; save first or pass --force"}
        log_carla("claramsg: quit requested%s" % (" (force)" if force else ""))
        if force:
            self.fHasUnsavedChanges = False
        # Bypass "minimize to tray": a quit command must actually quit.
        self.fForceQuit = True
        QTimer.singleShot(0, self.close)
        return {"ok": True}

    def handleMsgRequest(self, request):
        """Read-only control channel; mutating commands go through the same host slots."""
        cmd = request.get("cmd")
        if cmd == "status":
            return {"v": 1, "ok": True, "data": self.instanceStatus()}
        if cmd == "save":
            if not getattr(self, "fProjectFilename", ""):
                return {"v": 1, "ok": False, "error": {"code": "no_project", "message": "no project is open"}}
            try:
                self.saveProjectNow()
            except Exception as exc:
                return {"v": 1, "ok": False, "error": {"code": "failed", "message": f"save failed: {exc}"}}
            if getattr(self, "fHasUnsavedChanges", False):
                return {"v": 1, "ok": False, "error": {"code": "failed", "message": "save failed"}}
            return {"v": 1, "ok": True, "data": {"path": self.fProjectFilename}}

        if cmd == "list":
            return {"v": 1, "ok": True, "data": self.canvasSnapshot(include_ports=bool(request.get("full")))}
        if cmd == "open":
            path = request.get("path")
            if not path or not os.path.isfile(path):
                return {"v": 1, "ok": False, "error": {"code": "not_found", "message": "project not found: %s" % path}}
            if not self.queueControlOpen(path, interactive=False):
                return {"v": 1, "ok": False, "error": {"code": "dirty", "message": "unsaved changes; save the project first"}}
            return {"v": 1, "ok": True}
        if cmd == "events":
            return {"v": 1, "ok": True, "data": {"events": self.msgEvents(
                request.get("count", 50), request.get("tag"), request.get("level"))}}
        if cmd == "screenshot":
            result = self.msgScreenshot(request.get("path"), bool(request.get("dialog")))
            if not result.get("ok"):
                return {"v": 1, "ok": False, "error": {"code": "internal", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True, "data": result}
        if cmd == "plugin":
            result = self.msgPlugin(request.get("action"), request.get("plugin"),
                                    request.get("value"))
            if not result.get("ok"):
                return {"v": 1, "ok": False,
                        "error": {"code": "internal", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True, "data": result}
        if cmd == "quit":
            result = self.msgQuit(bool(request.get("force")))
            if not result.get("ok"):
                return {"v": 1, "ok": False,
                        "error": {"code": "dirty", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True}
        if cmd == "settings":
            result = self.msgSettings(request.get("action"), request.get("target"),
                                      request.get("value"), bool(request.get("force")))
            if not result.get("ok"):
                return {"v": 1, "ok": False,
                        "error": {"code": "internal", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True, "data": result}
        if cmd == "canvas":
            result = self.msgCanvas(request.get("action"), request.get("value"))
            if not result.get("ok"):
                return {"v": 1, "ok": False,
                        "error": {"code": "internal", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True, "data": result}
        if cmd == "dialogs":
            result = self.msgDialogs()
            if not result.get("ok"):
                return {"v": 1, "ok": False, "error": {"code": "internal", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True, "data": result}
        if cmd == "dialog":
            result = self.msgDialogAction(request.get("action"), request.get("text"), bool(request.get("force")))
            if not result.get("ok"):
                return {"v": 1, "ok": False, "error": {"code": "internal", "message": result.get("error", "failed")}}
            return {"v": 1, "ok": True, "data": result}
        if cmd == "replace":
            node = request.get("node")
            other = request.get("with")
            other_node = request.get("with_node")
            if (not isinstance(node, int)
                    or (other is not None and not isinstance(other, int))
                    or (other_node is not None and not isinstance(other_node, int))):
                return {"v": 1, "ok": False, "error": {"code": "bad_request", "message": "node and plugin ids must be integers"}}
            if other is not None and other_node is not None:
                return {"v": 1, "ok": False, "error": {"code": "bad_request", "message": "use with or with_node, not both"}}
            node = self._resolveNodePluginId(node)
            if other_node is not None:
                other = self._resolveNodePluginId(other_node)
            auto = bool(request.get("auto"))
            dry_run = bool(request.get("dry_run"))
            if auto or dry_run:
                result = self.showReplaceWithRewire(
                    node, auto=auto, with_plugin_id=other, dry_run=dry_run)
                if not result.get("ok"):
                    return {"v": 1, "ok": False, "error": {"code": "failed", "message": result.get("error", "failed")}}
                return {"v": 1, "ok": True, "data": result}
            QTimer.singleShot(0, lambda n=node, o=other: self.showReplaceWithRewire(n, with_plugin_id=o))
            return {"v": 1, "ok": True, "data": {"opened": True}}
        if cmd == "rewire_status":
            return {"v": 1, "ok": True, "data": getattr(self, "_rewireResult", {"done": True, "idle": True})}
        return {"v": 1, "ok": False, "error": {"code": "unsupported", "message": "unknown command: %s" % cmd}}

    def queueControlOpen(self, filename, interactive=True):
        """Accept an open request; never discard unsaved edits without an answer."""
        path = os.path.abspath(filename)
        current = os.path.abspath(self.fProjectFilename or "")
        if path == current:
            # Same project: the running window already has it; just raise it.
            if hasattr(self, "_restoreFromSystemTray"):
                self._restoreFromSystemTray()
            else:
                self.showIfNeeded()
            return True
        if getattr(self, "fHasUnsavedChanges", False):
            if not interactive:
                return False
            QTimer.singleShot(0, lambda p=path: self._promptControlOpen(p))
            return True
        self._pendingControlOpen = path
        QTimer.singleShot(500, self._applyControlOpen)
        return True

    def _promptControlOpen(self, path):
        answer = QMessageBox.question(
            self,
            self.tr("Unsaved Changes"),
            self.tr("This project has unsaved changes. Save before opening\n%s?") % path,
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Cancel:
            return
        if answer == QMessageBox.Save:
            self.saveProjectNow()
            if getattr(self, "fHasUnsavedChanges", False):
                return
        self._pendingControlOpen = path
        QTimer.singleShot(0, self._applyControlOpen)

    def _applyControlOpen(self):
        path = getattr(self, "_pendingControlOpen", None)
        if not path:
            return
        if getattr(self, "fIsProjectLoading", False):
            QTimer.singleShot(500, self._applyControlOpen)
            return
        self._pendingControlOpen = None
        self.openProjectFromControl(path)

    def openProjectFromControl(self, filename):
        """Same sequence as File -> Open: unload first, then load, so the engine never
        ends up with two projects' plugins at once."""
        try:
            if getattr(self, "fIsProjectLoading", False):
                return False
            filename = os.path.abspath(filename)
            if not os.path.isfile(filename):
                return False
            previous_filename = self.fProjectFilename
            previous_source = getattr(self, "fLastLoadedSource", None) or previous_filename
            if self.fPluginCount > 0:
                self.pluginRemoveAll()
            self.fProjectFilename = filename
            self.setProperWindowTitle()
            if self.loadProjectNow(source_override=filename):
                return True
            # The old plugins are already unloaded; put the previous session back.
            if previous_source and os.path.isfile(previous_source):
                logger.warning("APP", f"open failed; restoring previous project {previous_source}")
                self.fProjectFilename = previous_filename or previous_source
                self.setProperWindowTitle()
                try:
                    self.loadProjectNow(source_override=previous_source)
                except Exception as exc:
                    logger.warning("APP", f"restoring previous project failed: {exc}")
            return False
        except Exception as exc:
            logger.warning("APP", f"openProjectFromControl failed: {exc}")
            return False

