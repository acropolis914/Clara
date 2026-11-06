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

    def handleMsgRequest(self, request):
        """Read-only control channel; mutating commands go through the same host slots."""
        cmd = request.get("cmd")
        if cmd == "status":
            return {"v": 1, "ok": True, "data": self.instanceStatus()}
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

