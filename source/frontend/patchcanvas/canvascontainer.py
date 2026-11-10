#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Carla Improved (Clara) - Patchbay Layout Container
# Non-destructive backdrop container (VBox, HBox, Grid) for grouping canvas nodes.

from qt_compat import (
    QAction,
    QColor,
    QColorDialog,
    QCursor,
    QFont,
    QFontMetrics,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsTextItem,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPainter,
    QPainterPath,
    QPen,
    QPointF,
    QPushButton,
    QRectF,
    Qt,
    QTextCursor,
    QWidget,
    QWidgetAction,
)

from .canvasboxshadow import CanvasBoxShadow
from .theme import get_swatch_colors
from . import (
    canvas,
    CanvasBoxType,
    CanvasContainerType,
    options,
)

CONTAINER_LAYOUT_VBOX = "vbox"
CONTAINER_LAYOUT_HBOX = "hbox"
CONTAINER_LAYOUT_GRID = "grid"
CONTAINER_LAYOUT_FREEFORM = "freeform"

CONTAINER_PADDING = 14.0
CONTAINER_HEADER_HEIGHT = 28.0
CONTAINER_ITEM_SPACING = 12.0
CONTAINER_MIN_WIDTH = 220.0

class CanvasContainer(QGraphicsObject):
    """
    Backdrop layout container for grouping patchbay nodes.
    Placed behind canvas items (z = -10). Moves child nodes without reparenting them,
    preserving cable trajectories and native port coordinates.
    """

    def __init__(
        self,
        container_id,
        title="Group",
        layout_mode=CONTAINER_LAYOUT_VBOX,
        parent=None,
    ):
        super().__init__(parent)

        self.m_id = container_id
        self.m_title = title
        self.m_layout_mode = layout_mode
        self.m_collapsed = False
        self.m_color = QColor(canvas.theme.color_accent)

        # Ordered list of child CanvasBox items currently attached
        self.m_items = []
        # Relative coordinate offsets: box -> (rel_x, rel_y) from container origin
        self.m_item_offsets = {}
        # Standby/ghost member descriptors: [{"plugin_id": ..., "pw_node_name": ..., "name": ..., "split_mode": ...}]
        self.m_standby_descriptors = []

        # Geometry
        self.m_width = CONTAINER_MIN_WIDTH
        self.m_height = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
        self.m_expanded_height = self.m_height

        # Interaction state
        self.m_is_dragging = False
        self.m_is_resizing = False
        self.m_resize_edge = None
        self.m_drag_start_item_pos = QPointF(0, 0)
        self.m_drag_start_mouse_pos = QPointF(0, 0)
        self.m_drag_start_size = (self.m_width, self.m_height)
        self.m_hover_insert_idx = None
        self.m_active_hover_box = None

        # Inline title editor item
        self.m_title_editor_item = None

        # Graphics item configuration - strictly NO ItemIsMovable to avoid dual-offset drift!
        self.setZValue(-10.0)
        self.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        # Drop shadow so the container reads as a panel above the canvas.
        if getattr(options, "box_shadows", True) and not getattr(options, "software_render", False):
            self.m_shadow = CanvasBoxShadow(self)
            self.m_shadow.setFakeParent(self)
            self.setGraphicsEffect(self.m_shadow)
        else:
            self.m_shadow = None

    def updateTheme(self):
        if self.m_shadow is not None:
            self.m_shadow.setColor(canvas.theme.box_shadow)
        self.update()

    def type(self):
        return CanvasContainerType

    def boundingRect(self):
        h = CONTAINER_HEADER_HEIGHT if self.m_collapsed else self.m_height
        return QRectF(0, 0, self.m_width, h)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 8.0, 8.0)
        return path

    # -------------------------------------------------------------------------
    # Member & Lifecycle Management
    # -------------------------------------------------------------------------

    @staticmethod
    def getBoxDescriptor(box):
        """Generates a stable composite identifier for a CanvasBox."""
        return {
            "plugin_id": getattr(box, "m_plugin_id", -1),
            "pw_node_name": getattr(box, "pw_node_name", None),
            "name": getattr(box, "m_group_name", ""),
            "split_mode": getattr(box, "m_split_mode", 0)
            if hasattr(box, "m_split_mode")
            else (1 if getattr(box, "isSplit", lambda: False)() else 0),
        }

    def matchesDescriptor(self, box, desc):
        """Checks if a CanvasBox matches a stored descriptor."""
        p_id = getattr(box, "m_plugin_id", -1)
        desc_pid = desc.get("plugin_id", -1)
        if p_id >= 0 and desc_pid >= 0:
            return p_id == desc_pid

        pw_name = getattr(box, "pw_node_name", None)
        if pw_name and desc.get("pw_node_name"):
            return pw_name == desc.get("pw_node_name")

        box_name = getattr(box, "m_group_name", "")
        desc_name = desc.get("name", "")
        if box_name and desc_name and box_name == desc_name:
            box_split = getattr(box, "m_split_mode", 0) if hasattr(box, "m_split_mode") else (1 if getattr(box, "isSplit", lambda: False)() else 0)
            desc_split = desc.get("split_mode", 0)
            return box_split == desc_split

        return False

    def addItem(self, box, index=None):
        if box in self.m_items:
            return
        if index is None or index < 0 or index > len(self.m_items):
            self.m_items.append(box)
        else:
            self.m_items.insert(index, box)

        setattr(box, "_canvas_container", self)
        # Remove from standby list if it was resting there
        self.m_standby_descriptors = [
            d for d in self.m_standby_descriptors if not self.matchesDescriptor(box, d)
        ]
        self.updateLayout()

    def removeItem(self, box, to_standby=False):
        if box in self.m_items:
            self.m_items.remove(box)
            if box in self.m_item_offsets:
                del self.m_item_offsets[box]
            if hasattr(box, "_canvas_container"):
                delattr(box, "_canvas_container")
            if to_standby:
                desc = self.getBoxDescriptor(box)
                if desc not in self.m_standby_descriptors:
                    self.m_standby_descriptors.append(desc)
            self.updateLayout()

    def containsBox(self, box):
        return box in self.m_items

    # -------------------------------------------------------------------------
    # Layout Solvers
    # -------------------------------------------------------------------------

    def addFreeformItem(self, box, rel_x=None, rel_y=None):
        if box not in self.m_items:
            self.m_items.append(box)
        setattr(box, "_canvas_container", self)
        if rel_x is None or rel_y is None:
            rel_x = box.x() - self.x()
            rel_y = box.y() - self.y()
        self.m_item_offsets[box] = (
            max(CONTAINER_PADDING, rel_x),
            max(CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING, rel_y),
        )
        self.updateLayout()

    def _canResize(self):
        """VBox/HBox size themselves from their members."""
        return self.m_layout_mode in (CONTAINER_LAYOUT_GRID, CONTAINER_LAYOUT_FREEFORM)

    def _contentMinSize(self):
        """Smallest frame that still contains every member and the padding."""
        min_w = self._headerMinWidth()
        min_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
        for box in self.m_items:
            if box is None:
                continue
            rel = self.m_item_offsets.get(box)
            if rel is None:
                rel = (
                    max(CONTAINER_PADDING, box.x() - self.x()),
                    max(CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING, box.y() - self.y()),
                )
            rect = box.boundingRect()
            min_w = max(min_w, rel[0] + rect.width() + CONTAINER_PADDING)
            min_h = max(min_h, rel[1] + rect.height() + CONTAINER_PADDING)
        return min_w, min_h

    def _headerMinWidth(self):
        """Narrowest frame that still fits the header controls and the title."""
        font = QFont()
        font.setBold(True)
        font.setPixelSize(12)
        fm = QFontMetrics(font)
        return max(120.0, 88.0 + fm.horizontalAdvance(self.m_title) + 12)

    def updateLayout(self):
        """Computes positions of member nodes and resizes container frame with zero drift."""
        if not self.m_items:
            self.prepareGeometryChange()
            self.m_width = CONTAINER_MIN_WIDTH
            self.m_height = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
            self.m_item_offsets.clear()
            self.update()
            return

        start_rel_x = CONTAINER_PADDING
        start_rel_y = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING

        if self.m_layout_mode == CONTAINER_LAYOUT_FREEFORM:
            # Calculate bounding hull of child nodes relative to container origin
            min_x = min_y = float("inf")
            max_r = max_b = float("-inf")
            for box in self.m_items:
                if box not in self.m_item_offsets:
                    self.m_item_offsets[box] = (
                        max(start_rel_x, box.x() - self.x()),
                        max(start_rel_y, box.y() - self.y()),
                    )
                rx, ry = self.m_item_offsets[box]
                min_x = min(min_x, rx)
                min_y = min(min_y, ry)
                max_r = max(max_r, rx + box.boundingRect().width())
                max_b = max(max_b, ry + box.boundingRect().height())

            new_w = max(self._headerMinWidth(), max_r + CONTAINER_PADDING)
            new_h = max(
                CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2,
                max_b + CONTAINER_PADDING,
            )

        elif self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
            self.m_item_offsets.clear()
            max_w = max(b.boundingRect().width() for b in self.m_items)
            current_y = start_rel_y
            for box in self.m_items:
                self.m_item_offsets[box] = (start_rel_x, current_y)
                current_y += box.boundingRect().height() + CONTAINER_ITEM_SPACING

            total_h = current_y - start_rel_y - CONTAINER_ITEM_SPACING
            new_w = max(self._headerMinWidth(), max_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + total_h

        elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
            self.m_item_offsets.clear()
            max_h = max(b.boundingRect().height() for b in self.m_items)
            current_x = start_rel_x
            for box in self.m_items:
                self.m_item_offsets[box] = (current_x, start_rel_y)
                current_x += box.boundingRect().width() + CONTAINER_ITEM_SPACING

            total_w = current_x - start_rel_x - CONTAINER_ITEM_SPACING
            new_w = max(self._headerMinWidth(), total_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + max_h

        else:  # Grid (2-column default)
            self.m_item_offsets.clear()
            cols = 2
            col_widths = [0] * cols
            for idx, box in enumerate(self.m_items):
                c = idx % cols
                col_widths[c] = max(col_widths[c], box.boundingRect().width())

            current_y = start_rel_y
            row_max_h = 0
            for idx, box in enumerate(self.m_items):
                c = idx % cols
                if c == 0 and idx > 0:
                    current_y += row_max_h + CONTAINER_ITEM_SPACING
                    row_max_h = 0
                bx = (
                    start_rel_x
                    if c == 0
                    else start_rel_x + col_widths[0] + CONTAINER_ITEM_SPACING
                )
                self.m_item_offsets[box] = (bx, current_y)
                row_max_h = max(row_max_h, box.boundingRect().height())

            total_w = sum(col_widths) + (cols - 1) * CONTAINER_ITEM_SPACING
            total_h = (current_y + row_max_h) - start_rel_y
            new_w = max(self._headerMinWidth(), total_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + total_h

        self.prepareGeometryChange()
        self.m_width = new_w
        self.m_height = new_h
        if not self.m_collapsed:
            self.m_expanded_height = new_h

        # Apply absolute coordinates strictly anchored to container origin
        self.syncChildrenPositions()
        self.update()

    def getHeaderPortScenePos(self, port, is_output=True):
        """Returns the scene coordinate along the container header for a port on collapse."""
        c_pos = self.pos()
        w = self.m_width
        y = c_pos.y() + CONTAINER_HEADER_HEIGHT / 2.0
        if is_output:
            return QPointF(c_pos.x() + w, y)
        else:
            return QPointF(c_pos.x(), y)

    def syncChildrenPositions(self):
        """Positions all child boxes precisely at container.pos() + offset without cumulative drift."""
        c_pos = self.pos()
        visible = not self.m_collapsed
        for box, (rel_x, rel_y) in self.m_item_offsets.items():
            box.setVisible(visible)
            if visible:
                box.blockSignals(True)
                box.setPos(c_pos.x() + rel_x, c_pos.y() + rel_y)
                box.blockSignals(False)
            box.repaintLines(forced=True)
            for conn in box.m_connection_lines:
                conn.line.setVisible(True)
                conn.line.updateLinePos()

    def toggleCollapse(self):
        self.m_collapsed = not self.m_collapsed
        self.prepareGeometryChange()
        self.syncChildrenPositions()
        self.update()

    # -------------------------------------------------------------------------
    # Drag & Drop Interception
    # -------------------------------------------------------------------------

    def calculateInsertionIndex(self, scene_pos):
        """Calculates nearest insertion slot index based on mouse scene coordinates."""
        if not self.m_items:
            return 0

        if self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
            target_y = scene_pos.y()
            for idx, box in enumerate(self.m_items):
                b_center_y = box.scenePos().y() + box.boundingRect().height() / 2.0
                if target_y < b_center_y:
                    return idx
            return len(self.m_items)

        elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
            target_x = scene_pos.x()
            for idx, box in enumerate(self.m_items):
                b_center_x = box.scenePos().x() + box.boundingRect().width() / 2.0
                if target_x < b_center_x:
                    return idx
            return len(self.m_items)

        return len(self.m_items)

    def setHoverPreview(self, box, scene_pos):
        self.m_active_hover_box = box
        self.m_hover_insert_idx = self.calculateInsertionIndex(scene_pos)
        self.update()

    def clearHoverPreview(self):
        if self.m_hover_insert_idx is not None or self.m_active_hover_box is not None:
            self.m_hover_insert_idx = None
            self.m_active_hover_box = None
            self.update()

    # -------------------------------------------------------------------------
    # Movement Lockstep (Zero Drift)
    # -------------------------------------------------------------------------

    def hoverMoveEvent(self, event):
        pos = event.pos()
        rect = self.boundingRect()
        margin = 10.0

        # Don't show resize cursor if collapsed or auto-sized
        if not self.m_collapsed and self._canResize():
            at_right = abs(pos.x() - rect.width()) <= margin
            at_bottom = abs(pos.y() - rect.height()) <= margin
            if at_right and at_bottom:
                self.setCursor(QCursor(Qt.SizeFDiagCursor))
                return
            elif at_right:
                self.setCursor(QCursor(Qt.SizeHorCursor))
                return
            elif at_bottom:
                self.setCursor(QCursor(Qt.SizeVerCursor))
                return

        if pos.y() <= CONTAINER_HEADER_HEIGHT:
            if pos.x() >= rect.width() - 110:
                self.setCursor(QCursor(Qt.PointingHandCursor))
                return
            self.setCursor(QCursor(Qt.SizeAllCursor))
            return

        self.setCursor(QCursor(Qt.ArrowCursor))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            rect = self.boundingRect()
            margin = 10.0

            # 1. Check resize handle on bottom/right corners (when expanded and resizable)
            if not self.m_collapsed and self._canResize():
                at_right = abs(pos.x() - rect.width()) <= margin
                at_bottom = abs(pos.y() - rect.height()) <= margin
                if at_right or at_bottom:
                    self.m_is_resizing = True
                    self.m_resize_edge = (at_right, at_bottom)
                    self.m_drag_start_mouse_pos = event.scenePos()
                    self.m_drag_start_size = (self.m_width, self.m_height)
                    event.accept()
                    return

            # 2. Check header controls
            if pos.y() <= CONTAINER_HEADER_HEIGHT:
                # Close/ungroup button [󰅖]: x = 8 to 26
                if 8.0 <= pos.x() <= 26.0:
                    event.accept()
                    self.ungroup()
                    return

                # Collapse / Expand button [󰍡]: x = 28 to 46
                if 28.0 <= pos.x() <= 46.0:
                    event.accept()
                    self.toggleCollapse()
                    return

                # Layout switcher badge: x = 48 to 72
                if 48.0 <= pos.x() <= 72.0:
                    event.accept()
                    modes = [
                        CONTAINER_LAYOUT_VBOX,
                        CONTAINER_LAYOUT_HBOX,
                        CONTAINER_LAYOUT_GRID,
                        CONTAINER_LAYOUT_FREEFORM,
                    ]
                    next_idx = (modes.index(self.m_layout_mode) + 1) % len(modes)
                    self.m_layout_mode = modes[next_idx]
                    self.updateLayout()
                    return

                # Header dragging
                self.m_is_dragging = True
                self.m_drag_start_item_pos = self.pos()
                self.m_drag_start_mouse_pos = event.scenePos()
                event.accept()
                return

            # Clicking container backdrop selects it
            self.setSelected(True)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.m_is_resizing:
            delta = event.scenePos() - self.m_drag_start_mouse_pos
            orig_w, orig_h = self.m_drag_start_size
            rx, ry = self.m_resize_edge
            min_w, min_h = self._contentMinSize()
            new_w = max(min_w, orig_w + delta.x()) if rx else orig_w
            new_h = max(min_h, orig_h + delta.y()) if ry else orig_h
            self.prepareGeometryChange()
            self.m_width = new_w
            self.m_height = new_h
            self.m_expanded_height = new_h
            self.update()
            event.accept()
            return

        if self.m_is_dragging:
            delta = event.scenePos() - self.m_drag_start_mouse_pos
            self.setPos(self.m_drag_start_item_pos + delta)
            self.syncChildrenPositions()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.m_is_resizing:
            self.m_is_resizing = False
            self.m_resize_edge = None
            event.accept()
            return
        if self.m_is_dragging:
            self.m_is_dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (
            event.button() == Qt.LeftButton
            and event.pos().y() <= CONTAINER_HEADER_HEIGHT
        ):
            # Inline rename collision: starts after controls (x >= 78) and limited to title length with min 5 chars
            font = QFont()
            font.setBold(True)
            font.setPixelSize(12)
            fm = QFontMetrics(font)
            min_width = fm.horizontalAdvance("MMMMM")  # min 5 characters width
            title_width = max(min_width, fm.horizontalAdvance(self.m_title) + 12)
            title_rect = QRectF(78.0, 0, title_width, CONTAINER_HEADER_HEIGHT)

            if title_rect.contains(event.pos()):
                event.accept()
                self.startInlineRename()
                return
        super().mouseDoubleClickEvent(event)

    def startInlineRename(self):
        if self.m_title_editor_item is not None:
            return

        text_item = QGraphicsTextItem(self)
        text_item.setPlainText(self.m_title)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(12)
        text_item.setFont(font)
        text_item.setDefaultTextColor(QColor(canvas.theme.color_text))
        text_item.setPos(74.0, 3.0)
        text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        text_item.setZValue(100.0)
        self.m_title_editor_item = text_item

        container = self

        def finish_edit():
            if container.m_title_editor_item is None:
                return
            new_txt = text_item.toPlainText().strip()
            if new_txt:
                container.m_title = new_txt
            it = container.m_title_editor_item
            container.m_title_editor_item = None
            if it.scene():
                it.scene().removeItem(it)
            container.update()

        def text_keyPressEvent(ev):
            if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
                ev.accept()
                finish_edit()
                return
            elif ev.key() == Qt.Key_Escape:
                ev.accept()
                if container.m_title_editor_item is not None:
                    it = container.m_title_editor_item
                    container.m_title_editor_item = None
                    if it.scene():
                        it.scene().removeItem(it)
                    container.update()
                return
            QGraphicsTextItem.keyPressEvent(text_item, ev)

        def text_focusOutEvent(ev):
            finish_edit()
            QGraphicsTextItem.focusOutEvent(text_item, ev)

        text_item.keyPressEvent = text_keyPressEvent
        text_item.focusOutEvent = text_focusOutEvent
        text_item.setFocus()

        # Select all text
        cursor = text_item.textCursor()
        cursor.select(
            QTextCursor.SelectionType.Document
            if hasattr(QTextCursor, "SelectionType")
            else QTextCursor.Document
        )
        text_item.setTextCursor(cursor)
        self.update()

    # -------------------------------------------------------------------------
    # Context Menu & Actions
    # -------------------------------------------------------------------------

    def autoArrangeMembers(self):
        """Order members by signal flow, then apply the container's layout."""
        nodes = [box for box in self.m_items if box is not None]
        if len(nodes) >= 2:
            try:
                from .patchcanvas import _nodeGraph, syncNodePositions

                all_nodes = []
                for group in canvas.group_list:
                    for widget in group.widgets:
                        if widget is not None:
                            all_nodes.append(widget)

                edges, _incoming, _names = _nodeGraph(all_nodes)
                layer = {node: 0 for node in all_nodes}
                for _ in range(len(all_nodes)):
                    changed = False
                    for source, targets in edges.items():
                        for target in targets:
                            if layer.get(target, 0) < layer.get(source, 0) + 1:
                                layer[target] = layer[source] + 1
                                changed = True
                    if not changed:
                        break

                nodes.sort(key=lambda node: (layer.get(node, 0), node.x()))
                self.m_items = nodes
                if self.m_layout_mode == CONTAINER_LAYOUT_FREEFORM:
                    x = self.x() + CONTAINER_PADDING
                    y = self.y() + CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING
                    for node in nodes:
                        node.setPos(x, y)
                        x += node.boundingRect().width() + 40
                    # refresh freeform offsets so updateLayout keeps the new row
                    self.m_item_offsets = {
                        node: (node.x() - self.x(), node.y() - self.y()) for node in nodes
                    }
                    syncNodePositions(nodes)
            except Exception as e:
                from .utils import log_carla
                log_carla(f"CanvasContainer::autoArrangeMembers('{self.m_title}') failed: {e}", level="warn")
        self.updateLayout()
        if self.scene() is not None:
            self.scene().update()

    def contextMenuEvent(self, event):
        menu = QMenu()

        act_rename = menu.addAction("Rename...")
        act_rename.triggered.connect(self.promptRename)

        # Layout Modes
        layout_menu = menu.addMenu("Layout Mode")
        act_vbox = layout_menu.addAction("VBox (Vertical)")
        act_hbox = layout_menu.addAction("HBox (Horizontal)")
        act_grid = layout_menu.addAction("Grid (Matrix)")
        act_freeform = layout_menu.addAction("Freeform (Unconstrained)")
        act_vbox.setCheckable(True)
        act_hbox.setCheckable(True)
        act_grid.setCheckable(True)
        act_freeform.setCheckable(True)
        act_vbox.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_VBOX)
        act_hbox.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_HBOX)
        act_grid.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_GRID)
        act_freeform.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_FREEFORM)

        act_vbox.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_VBOX))
        act_hbox.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_HBOX))
        act_grid.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_GRID))
        act_freeform.triggered.connect(
            lambda: self.setLayoutMode(CONTAINER_LAYOUT_FREEFORM)
        )

        act_auto_arrange = menu.addAction("Auto-Arrange Members")
        act_auto_arrange.triggered.connect(self.autoArrangeMembers)

        # Color context menu with Catppuccin palette swatches
        color_menu = QMenu("Color", menu)
        palette_widget = QWidget()
        pal_layout = QHBoxLayout(palette_widget)
        pal_layout.setContentsMargins(6, 4, 6, 4)
        pal_layout.setSpacing(4)

        swatch_colors = get_swatch_colors()
        theme = canvas.theme

        # Reset button
        btn_reset = QPushButton("✕")
        btn_reset.setToolTip("Reset to Default Color")
        btn_reset.setFixedSize(22, 22)
        btn_reset.setStyleSheet(
            "QPushButton { font-weight: bold; color: %s; background: transparent;"
            " border: 1px solid %s; border-radius: 3px; }"
            "QPushButton:hover { color: %s; border-color: %s; background: %s; }"
            % (theme.color_muted.name(), theme.color_muted.name(),
               theme.color_text.name(), theme.color_text.name(),
               theme.color_surface.name())
        )
        btn_reset.clicked.connect(
            lambda: (self.setColor(QColor(theme.color_accent)), menu.close())
        )
        pal_layout.addWidget(btn_reset)

        for col_hex, col_name in swatch_colors:
            btn_col = QPushButton()
            btn_col.setToolTip(col_name)
            btn_col.setFixedSize(22, 22)
            btn_col.setStyleSheet(
                "QPushButton { background-color: %s; border: 1px solid %s;"
                " border-radius: 3px; }"
                "QPushButton:hover { border: 2px solid %s; }"
                % (col_hex, theme.color_muted.name(), theme.color_text.name())
            )
            btn_col.clicked.connect(
                lambda checked=False, c=col_hex: (
                    self.setColor(QColor(c)),
                    menu.close(),
                )
            )
            pal_layout.addWidget(btn_col)

        color_widget_action = QWidgetAction(color_menu)
        color_widget_action.setDefaultWidget(palette_widget)
        color_menu.addAction(color_widget_action)
        color_menu.addSeparator()

        def pickCustomColor():
            menu.close()
            initial = self.m_color if self.m_color else QColor(canvas.theme.color_accent)
            chosen = QColorDialog.getColor(initial, None, "Select Container Color")
            if chosen.isValid():
                self.setColor(chosen)

        act_custom_color = color_menu.addAction("Custom Color...")
        act_custom_color.triggered.connect(pickCustomColor)

        act_reset_color = color_menu.addAction("Reset Color")
        act_reset_color.triggered.connect(
            lambda: (self.setColor(QColor(canvas.theme.color_accent)), menu.close())
        )

        menu.addMenu(color_menu)

        menu.addSeparator()

        act_collapse = menu.addAction("Expand" if self.m_collapsed else "Collapse")
        act_collapse.triggered.connect(self.toggleCollapse)

        act_ungroup = menu.addAction("Ungroup Container")
        act_ungroup.triggered.connect(self.ungroup)

        menu.exec_(event.screenPos())
        event.accept()

    def promptRename(self):
        self.startInlineRename()

    def promptCustomColor(self):
        chosen = QColorDialog.getColor(
            self.m_color, None, "Select Container Accent Color"
        )
        if chosen.isValid():
            self.setColor(chosen)

    def setColor(self, color):
        self.m_color = QColor(color) if isinstance(color, str) else color
        self.update()

    def setLayoutMode(self, mode):
        self.m_layout_mode = mode
        self.updateLayout()

    def ungroup(self):
        reply = QMessageBox.question(
            None,
            "Ungroup Container",
            f"Are you sure you want to ungroup '{self.m_title}'?\nAll items will remain on the canvas.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        from .patchcanvas import ungroupNode

        # Ensure all boxes are visible and keep their current canvas coordinates
        if self.m_collapsed:
            self.toggleCollapse()

        for b in list(self.m_items):
            ungroupNode(b)

    def dissolve(self):
        self.ungroup()

    # -------------------------------------------------------------------------
    # Painting & Visual Rendering
    # -------------------------------------------------------------------------

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.boundingRect()

        theme = canvas.theme

        # 1. Background Frame Panel
        bg_color = QColor(theme.color_surface)
        bg_color.setAlpha(195)
        painter.setBrush(bg_color)
        pen_color = self.m_color
        pen = QPen(pen_color, 1.5)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 8.0, 8.0)

        # 2. Header Bar
        header_rect = QRectF(0, 0, rect.width(), CONTAINER_HEADER_HEIGHT)
        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, 8.0, 8.0)
        painter.fillPath(
            header_path,
            QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 50),
        )

        font = QFont(painter.font())

        # 1. Close / ungroup button [󰅖] (x: 8 to 26)
        painter.setPen(QColor(theme.color_danger))
        font.setBold(True)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(
            QRectF(8, 0, 18, CONTAINER_HEADER_HEIGHT),
            Qt.AlignVCenter | Qt.AlignCenter,
            "󰅖",
        )

        # 2. Collapse toggle [󰍡 / 󰍢] (x: 28 to 46)
        collapse_icon = "󰪦" if self.m_collapsed else "󰘖"
        painter.setPen(QColor(theme.color_muted))
        painter.drawText(
            QRectF(28, 0, 18, CONTAINER_HEADER_HEIGHT),
            Qt.AlignVCenter | Qt.AlignCenter,
            collapse_icon,
        )

        # 3. Layout switcher badge (x: 48 to 72)
        # VBOX: 󰝘, HBOX: 󰝙, GRID: 󰝚, FREEFORM: 󰝜
        layout_icons = {
            CONTAINER_LAYOUT_VBOX: "󱇍",
            CONTAINER_LAYOUT_HBOX: "󱇈",
            CONTAINER_LAYOUT_GRID: "󰕰",
            CONTAINER_LAYOUT_FREEFORM: "󰆟",
        }
        layout_icon = layout_icons.get(self.m_layout_mode, "󰝘")
        painter.setPen(QColor(theme.color_accent))
        painter.drawText(
            QRectF(48, 0, 24, CONTAINER_HEADER_HEIGHT),
            Qt.AlignVCenter | Qt.AlignCenter,
            layout_icon,
        )

        # 4. Title text (hidden while inline editing, positioned at x=78)
        if self.m_title_editor_item is None:
            painter.setPen(QColor(theme.color_text))
            font.setBold(True)
            font.setPixelSize(12)
            painter.setFont(font)
            painter.drawText(
                QRectF(78, 0, rect.width() - 88, CONTAINER_HEADER_HEIGHT),
                Qt.AlignVCenter | Qt.AlignLeft,
                self.m_title,
            )

        if self.m_collapsed:
            return

        # 3. Disconnected standby chip notice if items are unplugged
        if self.m_standby_descriptors:
            standby_cnt = len(self.m_standby_descriptors)
            standby = QColor(theme.color_danger)
            standby.setAlpha(180)
            painter.setPen(standby)
            font.setItalic(True)
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(
                QRectF(10, rect.height() - 18, rect.width() - 20, 14),
                Qt.AlignVCenter | Qt.AlignLeft,
                f"• {standby_cnt} item{'s' if standby_cnt > 1 else ''} standby (unplugged)",
            )

        # 4. Interactive Drop Slot Indicator Line
        if self.m_hover_insert_idx is not None:
            painter.setPen(QPen(QColor(theme.color_accent), 2.5, Qt.DashLine))
            if self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
                if self.m_hover_insert_idx < len(self.m_items):
                    b = self.m_items[self.m_hover_insert_idx]
                    local_y = b.y() - self.y() - CONTAINER_ITEM_SPACING / 2.0
                else:
                    local_y = rect.height() - CONTAINER_PADDING / 2.0
                painter.drawLine(
                    QPointF(CONTAINER_PADDING, local_y),
                    QPointF(rect.width() - CONTAINER_PADDING, local_y),
                )
            elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
                if self.m_hover_insert_idx < len(self.m_items):
                    b = self.m_items[self.m_hover_insert_idx]
                    local_x = b.x() - self.x() - CONTAINER_ITEM_SPACING / 2.0
                else:
                    local_x = rect.width() - CONTAINER_PADDING / 2.0
                painter.drawLine(
                    QPointF(local_x, CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING),
                    QPointF(local_x, rect.height() - CONTAINER_PADDING),
                )

        # 5. Subtle resize grip marks at bottom-right corner
        grip = QColor(theme.color_muted)
        grip.setAlpha(80)
        painter.setPen(QPen(grip, 1.2))
        rw, rh = rect.width(), rect.height()
        painter.drawLine(QPointF(rw - 12, rh - 4), QPointF(rw - 4, rh - 12))
        painter.drawLine(QPointF(rw - 8, rh - 4), QPointF(rw - 4, rh - 8))
