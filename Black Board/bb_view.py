from PyQt6.QtWidgets import (
    QGraphicsView, QMenu, QColorDialog, QInputDialog
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QSurfaceFormat

from bb_constants import Tool, DEFAULT_DRAW_COLOR, THICKNESS_LEVELS, NODE_WIDTH
from bb_commands import AddItemCommand
from bb_connections import ConnectionLine
from bb_nodes import (
    BaseNode, DecisionNode, TableNode, ProcedureNode, ApiNode,
    NoteNode, GenericNode, PortItem, NODE_TYPES
)
from bb_draw_items import (
    StrokeItem, RectDrawItem, EllipseDrawItem, ArrowItem, TextLabelItem, DRAW_ITEM_TYPES
)

_NODE_CLS_MAP = {
    Tool.NODE_TABLE:    TableNode,
    Tool.NODE_DECISION: DecisionNode,
    Tool.NODE_PROC:     ProcedureNode,
    Tool.NODE_API:      ApiNode,
    Tool.NODE_NOTE:     NoteNode,
    Tool.NODE_GENERIC:  GenericNode,
}
_NODE_TOOLS = set(_NODE_CLS_MAP)


class BlackboardView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        fmt = QSurfaceFormat()
        fmt.setSamples(4)
        QSurfaceFormat.setDefaultFormat(fmt)
        self.setViewport(QOpenGLWidget())
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        self._tool         = Tool.SELECT
        self.draw_color    = DEFAULT_DRAW_COLOR
        self.draw_width    = 2
        self.conn_bidir    = False

        self._panning      = False
        self._pan_start    = QPointF()
        self._active_stroke = None
        self._active_shape  = None
        self._shape_origin  = None

    def set_tool(self, tool: Tool):
        self._tool = tool
        if tool == Tool.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif tool == Tool.SELECT:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        sc = self.scene()
        sp = self.mapToScene(event.pos())

        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning   = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            tool = self._tool

            if tool == Tool.SELECT:
                item = self.itemAt(event.pos())
                if isinstance(item, PortItem):
                    sc.start_connection(item)
                    event.accept()
                    return

            elif tool in _NODE_TOOLS:
                node = _NODE_CLS_MAP[tool](x=sp.x() - NODE_WIDTH / 2, y=sp.y() - 40)
                sc.undo_stack.push(AddItemCommand(sc, node, "Add Node"))
                event.accept()
                return

            elif tool == Tool.PEN:
                stroke = StrokeItem(self.draw_color, self.draw_width)
                path   = QPainterPath(sp)
                stroke.setPath(path)
                sc.addItem(stroke)
                self._active_stroke = stroke
                event.accept()
                return

            elif tool in (Tool.RECT, Tool.ELLIPSE, Tool.ARROW):
                self._shape_origin = sp
                if tool == Tool.RECT:
                    shape = RectDrawItem(QRectF(sp, QSizeF(1, 1)),
                                         self.draw_color, self.draw_width)
                elif tool == Tool.ELLIPSE:
                    shape = EllipseDrawItem(QRectF(sp, QSizeF(1, 1)),
                                            self.draw_color, self.draw_width)
                else:
                    shape = ArrowItem(sp, sp, self.draw_color, self.draw_width)
                sc.addItem(shape)
                self._active_shape = shape
                event.accept()
                return

            elif tool == Tool.TEXT:
                label = TextLabelItem("Text", sp, self.draw_color)
                sc.undo_stack.push(AddItemCommand(sc, label, "Add Text"))
                label.setFocus()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        sp = self.mapToScene(event.pos())

        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        if self._active_stroke and event.buttons() & Qt.MouseButton.LeftButton:
            path = self._active_stroke.path()
            path.lineTo(sp)
            self._active_stroke.setPath(path)
            event.accept()
            return

        if self._active_shape and self._shape_origin and \
                event.buttons() & Qt.MouseButton.LeftButton:
            o = self._shape_origin
            if isinstance(self._active_shape, (RectDrawItem, EllipseDrawItem)):
                self._active_shape.setRect(
                    QRectF(min(o.x(), sp.x()), min(o.y(), sp.y()),
                           abs(sp.x() - o.x()), abs(sp.y() - o.y())))
            elif isinstance(self._active_shape, ArrowItem):
                self._active_shape._p2 = sp
                self._active_shape._rebuild()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        sc = self.scene()

        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            cursor = (Qt.CursorShape.CrossCursor
                      if self._tool not in (Tool.SELECT, Tool.PAN)
                      else Qt.CursorShape.ArrowCursor)
            self.setCursor(cursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if sc._pending_source is not None:
                item = self.itemAt(event.pos())
                if isinstance(item, PortItem):
                    sc.finish_connection(item, self.draw_color, self.draw_width, self.conn_bidir)
                else:
                    sc._pending_source = None
                event.accept()
                return

            if self._active_stroke:
                stroke = self._active_stroke
                self._active_stroke = None
                sc.removeItem(stroke)
                sc.undo_stack.push(AddItemCommand(sc, stroke, "Draw Stroke"))
                event.accept()
                return

            if self._active_shape:
                shape = self._active_shape
                self._active_shape = None
                self._shape_origin = None
                sc.removeItem(shape)
                sc.undo_stack.push(AddItemCommand(sc, shape, "Draw Shape"))
                event.accept()
                return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.scene().delete_selected()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        sc   = self.scene()
        sp   = self.mapToScene(event.pos())
        item = self.itemAt(event.pos())
        menu = QMenu(self)

        if isinstance(item, NODE_TYPES):
            change_color = menu.addAction("Change Color…")
            rename_act   = menu.addAction("Rename…") if hasattr(item, "_title") else None
            menu.addSeparator()
            delete_act = menu.addAction("Delete")
            chosen = menu.exec(event.globalPos())
            if chosen == change_color:
                color = QColorDialog.getColor(item._body_color, self, "Pick Color")
                if color.isValid():
                    item.set_color(color)
            elif rename_act and chosen == rename_act:
                text, ok = QInputDialog.getText(self, "Rename", "Title:", text=item._title)
                if ok and text:
                    item._title = text
                    item._title_item.setPlainText(text)
            elif chosen == delete_act:
                item.setSelected(True)
                sc.delete_selected()

        elif isinstance(item, ConnectionLine):
            bidir_act  = menu.addAction(
                "Make One-Way" if item.bidirectional else "Make Bidirectional")
            color_act  = menu.addAction("Change Color…")
            width_acts = [menu.addAction(f"Thickness: {('Thin','Medium','Thick')[i]}")
                          for i in range(3)]
            menu.addSeparator()
            delete_act = menu.addAction("Delete Connection")
            chosen = menu.exec(event.globalPos())
            if chosen == bidir_act:
                item.bidirectional = not item.bidirectional
                item.update_path()
            elif chosen == color_act:
                color = QColorDialog.getColor(item._color, self, "Pick Line Color")
                if color.isValid():
                    item._color = color
                    item.update()
            elif chosen in width_acts:
                item._width = THICKNESS_LEVELS[width_acts.index(chosen)]
                item.update()
            elif chosen == delete_act:
                item.setSelected(True)
                sc.delete_selected()

        elif isinstance(item, TextLabelItem):
            edit_act   = menu.addAction("Edit Text…")
            border_act = menu.addAction("Remove Border" if item._show_border else "Add Border")
            bg_act     = menu.addAction("Set Background Color…")
            clear_bg   = menu.addAction("Clear Background")
            menu.addSeparator()
            delete_act = menu.addAction("Delete")
            chosen = menu.exec(event.globalPos())
            if chosen == edit_act:
                item._enter_edit()
            elif chosen == border_act:
                item._show_border = not item._show_border
                item.update()
            elif chosen == bg_act:
                start = item._bg_color or QColor("#2a2a3e")
                color = QColorDialog.getColor(start, self, "Background Color")
                if color.isValid():
                    item._bg_color = color
                    item.update()
            elif chosen == clear_bg:
                item._bg_color = None
                item.update()
            elif chosen == delete_act:
                item.setSelected(True)
                sc.delete_selected()

        elif isinstance(item, DRAW_ITEM_TYPES):
            delete_act = menu.addAction("Delete Drawing")
            if menu.exec(event.globalPos()) == delete_act:
                item.setSelected(True)
                sc.delete_selected()

        else:
            for label, tool in [
                ("Add Table Node",     Tool.NODE_TABLE),
                ("Add Decision Node",  Tool.NODE_DECISION),
                ("Add Procedure Node", Tool.NODE_PROC),
                ("Add API Node",       Tool.NODE_API),
                ("Add Note",           Tool.NODE_NOTE),
                ("Add Generic Node",   Tool.NODE_GENERIC),
            ]:
                act = menu.addAction(label)
                act.setData(tool)
            chosen = menu.exec(event.globalPos())
            if chosen and chosen.data():
                node = _NODE_CLS_MAP[chosen.data()](x=sp.x() - NODE_WIDTH / 2, y=sp.y() - 40)
                sc.undo_stack.push(AddItemCommand(sc, node, "Add Node"))
