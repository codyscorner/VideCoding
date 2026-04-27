from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QUndoStack

from bb_constants import BACKGROUND, GRID_MINOR, GRID_MAJOR, GRID_MINOR_SIZE, GRID_MAJOR_MULT
from bb_commands import AddItemCommand, DeleteItemsCommand
from bb_connections import ConnectionLine
from bb_nodes import BaseNode, NODE_TYPES
from bb_draw_items import (
    StrokeItem, RectDrawItem, EllipseDrawItem, ArrowItem, TextLabelItem, DRAW_ITEM_TYPES
)


class BlackboardScene(QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.undo_stack      = QUndoStack(self)
        self._pending_source = None

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, BACKGROUND)
        left   = int(rect.left())   - (int(rect.left())   % GRID_MINOR_SIZE)
        top    = int(rect.top())    - (int(rect.top())    % GRID_MINOR_SIZE)
        right  = int(rect.right())  + GRID_MINOR_SIZE
        bottom = int(rect.bottom()) + GRID_MINOR_SIZE
        minor_pen = QPen(GRID_MINOR, 0)
        major_pen = QPen(GRID_MAJOR, 0)
        x = left
        while x <= right:
            pen = major_pen if (x // GRID_MINOR_SIZE) % GRID_MAJOR_MULT == 0 else minor_pen
            painter.setPen(pen)
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += GRID_MINOR_SIZE
        y = top
        while y <= bottom:
            pen = major_pen if (y // GRID_MINOR_SIZE) % GRID_MAJOR_MULT == 0 else minor_pen
            painter.setPen(pen)
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += GRID_MINOR_SIZE

    def start_connection(self, port):
        self._pending_source = port

    def finish_connection(self, target_port,
                          color: QColor = QColor("#C8C8FF"),
                          width: int = 2,
                          bidirectional: bool = False) -> bool:
        src = self._pending_source
        self._pending_source = None
        if src is None or src is target_port:
            return False
        if src.role == target_port.role:
            return False
        if src.role == "target":
            src, target_port = target_port, src
        conn = ConnectionLine(src, target_port, color, width, bidirectional)
        self.undo_stack.push(AddItemCommand(self, conn, "Add Connection"))
        return True

    def delete_selected(self):
        nodes = [i for i in self.selectedItems() if isinstance(i, NODE_TYPES)]
        conns = [i for i in self.selectedItems() if isinstance(i, ConnectionLine)]
        draws = [i for i in self.selectedItems() if isinstance(i, DRAW_ITEM_TYPES)]
        for node in nodes:
            for port in (node.source_port, node.target_port):
                for conn in list(port.connections):
                    if conn not in conns:
                        conns.append(conn)
        if not nodes and not conns and not draws:
            return
        for conn in conns:
            conn.detach()
        self.undo_stack.push(DeleteItemsCommand(self, nodes, conns, draws))

    def to_dict(self, view_data: dict | None = None) -> dict:
        nodes = [i for i in self.items() if isinstance(i, NODE_TYPES)]
        conns = [i for i in self.items() if isinstance(i, ConnectionLine)]
        draws = [i for i in self.items() if isinstance(i, DRAW_ITEM_TYPES)]
        node_index = {id(n): idx for idx, n in enumerate(nodes)}
        conn_list  = [c for c in (c.to_dict(node_index) for c in conns) if c is not None]
        return {
            "version":     2,
            "nodes":       [n.to_dict() for n in nodes],
            "connections": conn_list,
            "drawings":    [d.to_dict() for d in draws],
            "view":        view_data or {},
        }

    def from_dict(self, data: dict) -> dict:
        self.clear()
        self.undo_stack.clear()
        self._pending_source = None

        nodes = []
        for nd in data.get("nodes", []):
            node = BaseNode.from_dict(nd)
            self.addItem(node)
            nodes.append(node)

        for cd in data.get("connections", []):
            src  = nodes[cd["source_node"]]
            dst  = nodes[cd["target_node"]]
            conn = ConnectionLine(
                src.source_port, dst.target_port,
                QColor(cd.get("color", "#C8C8FF")),
                cd.get("width", 2),
                cd.get("bidirectional", False),
            )
            self.addItem(conn)

        _loaders = {
            "stroke":  StrokeItem.from_dict,
            "rect":    RectDrawItem.from_dict,
            "ellipse": EllipseDrawItem.from_dict,
            "arrow":   ArrowItem.from_dict,
            "text":    TextLabelItem.from_dict,
        }
        for dd in data.get("drawings", []):
            loader = _loaders.get(dd.get("item_type"))
            if loader:
                self.addItem(loader(dd))

        return data.get("view", {})
