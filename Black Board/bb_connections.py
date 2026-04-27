import math
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QBrush, QPainterPath, QPolygonF, QColor

from bb_constants import NODE_SELECTED


class ConnectionLine(QGraphicsPathItem):
    """Directed bezier between ports. bidirectional = arrows on both ends."""

    ARROW_HEAD = 12

    def __init__(self, source_port, target_port,
                 color: QColor = QColor("#C8C8FF"),
                 width: int = 2,
                 bidirectional: bool = False):
        super().__init__()
        self.source_port   = source_port
        self.target_port   = target_port
        self._color        = color
        self._width        = width
        self.bidirectional = bidirectional
        source_port.connections.append(self)
        target_port.connections.append(self)
        self._bezier = QPainterPath()
        self._arrows: list[QPolygonF] = []
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_path()

    def _arrowhead_poly(self, tip: QPointF, toward: QPointF) -> QPolygonF:
        dx = tip.x() - toward.x()
        dy = tip.y() - toward.y()
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        h, s = self.ARROW_HEAD, self.ARROW_HEAD * 0.38
        return QPolygonF([
            tip,
            QPointF(tip.x() - ux * h - uy * s, tip.y() - uy * h + ux * s),
            QPointF(tip.x() - ux * h + uy * s, tip.y() - uy * h - ux * s),
        ])

    def update_path(self):
        src = self.source_port.scene_center()
        dst = self.target_port.scene_center()
        dx  = abs(dst.x() - src.x()) * 0.5 + 40

        cp1 = QPointF(src.x() + dx, src.y())
        cp2 = QPointF(dst.x() - dx, dst.y())

        self._bezier = QPainterPath(src)
        self._bezier.cubicTo(cp1, cp2, dst)

        near_dst = QPointF(dst.x() - dx * 0.05, dst.y())
        self._arrows = [self._arrowhead_poly(dst, near_dst)]

        if self.bidirectional:
            near_src = QPointF(src.x() + dx * 0.05, src.y())
            self._arrows.append(self._arrowhead_poly(src, near_src))

        self.setPath(self._bezier)

    def detach(self):
        if self in self.source_port.connections:
            self.source_port.connections.remove(self)
        if self in self.target_port.connections:
            self.target_port.connections.remove(self)

    def paint(self, painter, option, widget=None):
        color = NODE_SELECTED if self.isSelected() else self._color
        pen   = QPen(color, self._width + (1 if self.isSelected() else 0))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawPath(self._bezier)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        for poly in self._arrows:
            painter.drawPolygon(poly)

    def to_dict(self, node_index: dict) -> dict | None:
        si = self.source_port.parentItem()
        di = self.target_port.parentItem()
        if id(si) not in node_index or id(di) not in node_index:
            return None
        return {
            "source_node":   node_index[id(si)],
            "target_node":   node_index[id(di)],
            "color":         self._color.name(),
            "width":         self._width,
            "bidirectional": self.bidirectional,
        }
