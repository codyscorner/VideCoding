from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsPolygonItem, QGraphicsTextItem, QInputDialog
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF

from bb_constants import (
    NODE_BODY, NODE_HEADER, NODE_BORDER, NODE_SELECTED,
    PORT_SOURCE, PORT_TARGET, TEXT_COLOR, NOTE_COLOR, NOTE_BORDER,
    PORT_RADIUS, NODE_WIDTH, NODE_HEADER_H, ROW_H
)
from bb_commands import MoveNodeCommand


# ── Port ──────────────────────────────────────────────────────────────────────

class PortItem(QGraphicsEllipseItem):
    def __init__(self, role: str, parent: QGraphicsItem):
        r = PORT_RADIUS
        super().__init__(-r, -r, r * 2, r * 2, parent)
        self.role        = role
        self.connections = []
        color = PORT_SOURCE if role == "source" else PORT_TARGET
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(130), 1))
        self.setZValue(2)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def scene_center(self) -> QPointF:
        return self.mapToScene(QPointF(0, 0))


# ── Base Node ─────────────────────────────────────────────────────────────────

class BaseNode(QGraphicsRectItem):
    node_type = "BaseNode"

    def __init__(self, title: str, x: float, y: float, rows: list[str],
                 color: QColor | None = None):
        height = NODE_HEADER_H + max(1, len(rows)) * ROW_H + 8
        super().__init__(0, 0, NODE_WIDTH, height)
        self.setPos(x, y)
        self._rows       = rows
        self._title      = title
        self._body_color = color or NODE_BODY
        self._drag_start: QPointF | None = None

        self.setBrush(QBrush(self._body_color))
        self.setPen(QPen(NODE_BORDER, 1.5))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self._title_item = QGraphicsTextItem(title, self)
        self._title_item.setDefaultTextColor(TEXT_COLOR)
        self._title_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._title_item.setPos(6, 4)

        self._row_items: list[QGraphicsTextItem] = []
        small = QFont("Segoe UI", 8)
        for i, row in enumerate(rows):
            item = QGraphicsTextItem(row, self)
            item.setDefaultTextColor(TEXT_COLOR)
            item.setFont(small)
            item.setPos(8, NODE_HEADER_H + i * ROW_H + 2)
            self._row_items.append(item)

        mid_y = height / 2
        self.target_port = PortItem("target", self)
        self.target_port.setPos(0, mid_y)
        self.source_port = PortItem("source", self)
        self.source_port.setPos(NODE_WIDTH, mid_y)

    def set_color(self, color: QColor):
        self._body_color = color
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        r = self.rect()
        border_color = NODE_SELECTED if self.isSelected() else NODE_BORDER
        painter.setBrush(QBrush(self._body_color))
        painter.setPen(QPen(border_color, 2.5 if self.isSelected() else 1.5))
        painter.drawRoundedRect(r, 6, 6)
        header = QRectF(r.x(), r.y(), r.width(), NODE_HEADER_H)
        painter.setBrush(QBrush(NODE_HEADER))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(header, 6, 6)
        painter.drawRect(QRectF(r.x(), r.y() + NODE_HEADER_H - 6, r.width(), 6))
        painter.setPen(QPen(NODE_BORDER, 1))
        painter.drawLine(QPointF(r.x(), r.y() + NODE_HEADER_H),
                         QPointF(r.right(), r.y() + NODE_HEADER_H))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for port in (self.source_port, self.target_port):
                for conn in port.connections:
                    conn.update_path()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self._drag_start = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._drag_start is not None and self.pos() != self._drag_start:
            sc = self.scene()
            if hasattr(sc, "undo_stack"):
                sc.undo_stack.push(MoveNodeCommand(self, self._drag_start, self.pos()))
        self._drag_start = None

    def to_dict(self) -> dict:
        return {
            "type":  self.node_type,
            "title": self._title,
            "x":     self.pos().x(),
            "y":     self.pos().y(),
            "rows":  self._rows,
            "color": self._body_color.name(),
        }

    @staticmethod
    def from_dict(data: dict) -> "BaseNode":
        if data["type"] == "DecisionNode":
            return DecisionNode._from_dict(data)
        cls_map = {
            "TableNode":     TableNode,
            "ProcedureNode": ProcedureNode,
            "ApiNode":       ApiNode,
            "NoteNode":      NoteNode,
            "GenericNode":   GenericNode,
        }
        cls   = cls_map.get(data["type"], GenericNode)
        color = QColor(data.get("color", NODE_BODY.name()))
        return cls(x=data["x"], y=data["y"],
                   columns=data.get("rows"), color=color)


# ── Node subclasses ───────────────────────────────────────────────────────────

class TableNode(BaseNode):
    node_type = "TableNode"
    DEFAULT_COLUMNS = ["id  INT  PK", "name  VARCHAR(255)", "created_at  DATETIME"]

    def __init__(self, x=0, y=0, columns=None, color=None):
        super().__init__("Table", x, y,
                         columns or list(self.DEFAULT_COLUMNS), color or NODE_BODY)


class ProcedureNode(BaseNode):
    node_type = "ProcedureNode"
    DEFAULT_COLUMNS = ["@param1  IN", "@param2  OUT", "RETURNS  INT"]

    def __init__(self, x=0, y=0, columns=None, color=None):
        super().__init__("Stored Procedure", x, y,
                         columns or list(self.DEFAULT_COLUMNS), color or QColor(40, 55, 45))


class ApiNode(BaseNode):
    node_type = "ApiNode"
    DEFAULT_COLUMNS = ["Method: GET", "Route: /api/v1/", "Auth: Bearer"]

    def __init__(self, x=0, y=0, columns=None, color=None):
        super().__init__("API Endpoint", x, y,
                         columns or list(self.DEFAULT_COLUMNS), color or QColor(40, 40, 65))


class NoteNode(BaseNode):
    node_type = "NoteNode"
    DEFAULT_COLUMNS = ["Write your note here..."]

    def __init__(self, x=0, y=0, columns=None, color=None):
        super().__init__("Note", x, y,
                         columns or list(self.DEFAULT_COLUMNS), color or NOTE_COLOR)

    def paint(self, painter, option, widget=None):
        r = self.rect()
        border_color = NODE_SELECTED if self.isSelected() else NOTE_BORDER
        painter.setBrush(QBrush(self._body_color))
        painter.setPen(QPen(border_color, 2.5 if self.isSelected() else 1.5))
        painter.drawRoundedRect(r, 4, 4)
        painter.setPen(QPen(NOTE_BORDER.darker(120), 1))
        painter.drawLine(QPointF(r.x(), r.y() + NODE_HEADER_H),
                         QPointF(r.right(), r.y() + NODE_HEADER_H))


class GenericNode(BaseNode):
    node_type = "GenericNode"

    def __init__(self, x=0, y=0, columns=None, color=None, title="Node"):
        super().__init__(title, x, y,
                         columns or ["Field 1", "Field 2"], color or QColor(50, 48, 55))


# ── Decision Node (diamond, resizable) ────────────────────────────────────────

class ResizeHandle(QGraphicsRectItem):
    SIZE = 8

    def __init__(self, corner: str, parent: "DecisionNode"):
        s = self.SIZE
        super().__init__(-s / 2, -s / 2, s, s, parent)
        self.corner = corner
        self.setBrush(QBrush(QColor(200, 200, 255)))
        self.setPen(QPen(QColor(100, 100, 200), 1))
        self.setZValue(3)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._dragging = False
        self._drag_start_scene = QPointF()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_scene = event.scenePos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.parentItem()._resize_by_handle(
                self.corner, event.scenePos() - self._drag_start_scene)
            self._drag_start_scene = event.scenePos()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()


class DecisionNode(QGraphicsPolygonItem):
    node_type = "DecisionNode"

    def __init__(self, x=0, y=0, columns=None, color=None, w=160, h=80):
        super().__init__()
        self._title      = "Decision"
        self._body_color = color or QColor(70, 50, 30)
        self._drag_start: QPointF | None = None
        self._w = w
        self._h = h

        self.setPos(x, y)
        self.setBrush(QBrush(self._body_color))
        self.setPen(QPen(QColor(200, 140, 60), 2))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self._title_item = QGraphicsTextItem("Decision", self)
        self._title_item.setDefaultTextColor(TEXT_COLOR)
        self._title_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        self.source_port = PortItem("source", self)
        self.target_port = PortItem("target", self)

        self._handles = {
            corner: ResizeHandle(corner, self)
            for corner in ("top", "bottom", "left", "right")
        }
        for h in self._handles.values(): h.setVisible(False)
        self._rebuild()

    def _rebuild(self):
        w, h = self._w, self._h
        self.setPolygon(QPolygonF([
            QPointF(w / 2, 0), QPointF(w, h / 2),
            QPointF(w / 2, h), QPointF(0, h / 2),
        ]))
        br = self._title_item.boundingRect()
        self._title_item.setPos(w / 2 - br.width() / 2, h / 2 - br.height() / 2)
        self.source_port.setPos(w, h / 2)
        self.target_port.setPos(0, h / 2)
        self._handles["top"].setPos(w / 2, 0)
        self._handles["bottom"].setPos(w / 2, h)
        self._handles["left"].setPos(0, h / 2)
        self._handles["right"].setPos(w, h / 2)
        for port in (self.source_port, self.target_port):
            for conn in port.connections:
                conn.update_path()

    def _resize_by_handle(self, corner: str, delta: QPointF):
        MIN = 60
        w, h = self._w, self._h
        if corner == "right":
            w = max(MIN, w + delta.x() * 2)
        elif corner == "left":
            w = max(MIN, w - delta.x() * 2)
            self.setPos(self.pos() + QPointF(delta.x(), 0))
        elif corner == "bottom":
            h = max(MIN, h + delta.y() * 2)
        elif corner == "top":
            h = max(MIN, h - delta.y() * 2)
            self.setPos(self.pos() + QPointF(0, delta.y()))
        self._w, self._h = w, h
        self._rebuild()

    def set_color(self, color: QColor):
        self._body_color = color
        self.setBrush(QBrush(color))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for port in (self.source_port, self.target_port):
                for conn in port.connections:
                    conn.update_path()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            visible = self.isSelected()
            for h in self._handles.values(): h.setVisible(visible)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self._drag_start = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._drag_start is not None and self.pos() != self._drag_start:
            sc = self.scene()
            if hasattr(sc, "undo_stack"):
                sc.undo_stack.push(MoveNodeCommand(self, self._drag_start, self.pos()))
        self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        text, ok = QInputDialog.getText(None, "Edit Decision", "Label:", text=self._title)
        if ok and text:
            self._title = text
            self._title_item.setPlainText(text)
            self._rebuild()
        event.accept()

    def to_dict(self) -> dict:
        return {"type": "DecisionNode", "title": self._title,
                "x": self.pos().x(), "y": self.pos().y(),
                "rows": [], "color": self._body_color.name(),
                "w": self._w, "h": self._h}

    @staticmethod
    def _from_dict(data: dict) -> "DecisionNode":
        node = DecisionNode(
            x=data["x"], y=data["y"],
            color=QColor(data.get("color", "#46321e")),
            w=data.get("w", 160), h=data.get("h", 80)
        )
        if data.get("title"):
            node._title = data["title"]
            node._title_item.setPlainText(data["title"])
            node._rebuild()
        return node


# ── Type groups (used by scene / view) ───────────────────────────────────────
NODE_TYPES = (BaseNode, DecisionNode)
