import math
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsTextItem
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from bb_constants import TEXT_COLOR, DEFAULT_DRAW_COLOR


def _sync_handles(item):
    """Show handles only when item is selected."""
    visible = item.isSelected()
    for h in item._handles.values():
        h.setVisible(visible)


# ── Corner handle (shared by Rect, Ellipse, Arrow) ────────────────────────────

class _CornerHandle(QGraphicsRectItem):
    SIZE = 8

    def __init__(self, corner: str, parent: QGraphicsItem):
        s = self.SIZE
        super().__init__(-s / 2, -s / 2, s, s, parent)
        self.corner = corner
        self.setBrush(QBrush(QColor(200, 200, 255)))
        self.setPen(QPen(QColor(100, 100, 200), 1))
        self.setZValue(3)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        cursors = {
            "tl": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor,
            "bl": Qt.CursorShape.SizeBDiagCursor,
            "br": Qt.CursorShape.SizeFDiagCursor,
            "p1": Qt.CursorShape.CrossCursor,
            "p2": Qt.CursorShape.CrossCursor,
        }
        self.setCursor(cursors.get(corner, Qt.CursorShape.SizeAllCursor))
        self._dragging = False
        self._last = QPointF()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last = event.scenePos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.parentItem()._handle_drag(self.corner, event.scenePos() - self._last)
            self._last = event.scenePos()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()


_DRAW_FLAGS = (
    QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
    QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
)


# ── Stroke (freehand pen) ─────────────────────────────────────────────────────

class StrokeItem(QGraphicsPathItem):
    item_type = "stroke"

    def __init__(self, color: QColor = DEFAULT_DRAW_COLOR, width: int = 2):
        super().__init__()
        self._color = color
        self._width = width
        self.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setFlags(_DRAW_FLAGS)

    def to_dict(self) -> dict:
        pts = [{"x": self.path().elementAt(i).x,
                "y": self.path().elementAt(i).y,
                "t": int(self.path().elementAt(i).type)}
               for i in range(self.path().elementCount())]
        p = self.pos()
        return {"item_type": "stroke", "x": p.x(), "y": p.y(),
                "color": self._color.name(), "width": self._width, "pts": pts}

    @staticmethod
    def from_dict(d: dict) -> "StrokeItem":
        s = StrokeItem(QColor(d["color"]), d["width"])
        path = QPainterPath()
        for pt in d["pts"]:
            if pt["t"] == 0: path.moveTo(pt["x"], pt["y"])
            else:             path.lineTo(pt["x"], pt["y"])
        s.setPath(path)
        s.setPos(d["x"], d["y"])
        return s


# ── Rectangle ─────────────────────────────────────────────────────────────────

class RectDrawItem(QGraphicsRectItem):
    item_type = "rect"

    def __init__(self, rect: QRectF, color: QColor = DEFAULT_DRAW_COLOR, width: int = 2):
        super().__init__(rect)
        self._color = color
        self._width = width
        self.setPen(QPen(color, width))
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setFlags(_DRAW_FLAGS)
        self._handles = {c: _CornerHandle(c, self) for c in ("tl", "tr", "bl", "br")}
        for h in self._handles.values(): h.setVisible(False)
        self._update_handles()

    def _update_handles(self):
        r = self.rect()
        self._handles["tl"].setPos(r.left(),  r.top())
        self._handles["tr"].setPos(r.right(), r.top())
        self._handles["bl"].setPos(r.left(),  r.bottom())
        self._handles["br"].setPos(r.right(), r.bottom())

    def _handle_drag(self, corner: str, delta: QPointF):
        r, MIN = self.rect(), 10
        if corner == "tl":
            r.setLeft(min(r.left() + delta.x(), r.right() - MIN))
            r.setTop(min(r.top() + delta.y(), r.bottom() - MIN))
        elif corner == "tr":
            r.setRight(max(r.right() + delta.x(), r.left() + MIN))
            r.setTop(min(r.top() + delta.y(), r.bottom() - MIN))
        elif corner == "bl":
            r.setLeft(min(r.left() + delta.x(), r.right() - MIN))
            r.setBottom(max(r.bottom() + delta.y(), r.top() + MIN))
        elif corner == "br":
            r.setRight(max(r.right() + delta.x(), r.left() + MIN))
            r.setBottom(max(r.bottom() + delta.y(), r.top() + MIN))
        self.setRect(r)
        self._update_handles()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            _sync_handles(self)
        return super().itemChange(change, value)

    def to_dict(self) -> dict:
        r, p = self.rect(), self.pos()
        return {"item_type": "rect", "x": p.x(), "y": p.y(),
                "rx": r.x(), "ry": r.y(), "rw": r.width(), "rh": r.height(),
                "color": self._color.name(), "width": self._width}

    @staticmethod
    def from_dict(d: dict) -> "RectDrawItem":
        item = RectDrawItem(QRectF(d["rx"], d["ry"], d["rw"], d["rh"]),
                            QColor(d["color"]), d["width"])
        item.setPos(d["x"], d["y"])
        return item


# ── Ellipse ───────────────────────────────────────────────────────────────────

class EllipseDrawItem(QGraphicsEllipseItem):
    item_type = "ellipse"

    def __init__(self, rect: QRectF, color: QColor = DEFAULT_DRAW_COLOR, width: int = 2):
        super().__init__(rect)
        self._color = color
        self._width = width
        self.setPen(QPen(color, width))
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setFlags(_DRAW_FLAGS)
        self._handles = {c: _CornerHandle(c, self) for c in ("tl", "tr", "bl", "br")}
        for h in self._handles.values(): h.setVisible(False)
        self._update_handles()

    def _update_handles(self):
        r = self.rect()
        self._handles["tl"].setPos(r.left(),  r.top())
        self._handles["tr"].setPos(r.right(), r.top())
        self._handles["bl"].setPos(r.left(),  r.bottom())
        self._handles["br"].setPos(r.right(), r.bottom())

    def _handle_drag(self, corner: str, delta: QPointF):
        r, MIN = self.rect(), 10
        if corner == "tl":
            r.setLeft(min(r.left() + delta.x(), r.right() - MIN))
            r.setTop(min(r.top() + delta.y(), r.bottom() - MIN))
        elif corner == "tr":
            r.setRight(max(r.right() + delta.x(), r.left() + MIN))
            r.setTop(min(r.top() + delta.y(), r.bottom() - MIN))
        elif corner == "bl":
            r.setLeft(min(r.left() + delta.x(), r.right() - MIN))
            r.setBottom(max(r.bottom() + delta.y(), r.top() + MIN))
        elif corner == "br":
            r.setRight(max(r.right() + delta.x(), r.left() + MIN))
            r.setBottom(max(r.bottom() + delta.y(), r.top() + MIN))
        self.setRect(r)
        self._update_handles()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            _sync_handles(self)
        return super().itemChange(change, value)

    def to_dict(self) -> dict:
        r, p = self.rect(), self.pos()
        return {"item_type": "ellipse", "x": p.x(), "y": p.y(),
                "rx": r.x(), "ry": r.y(), "rw": r.width(), "rh": r.height(),
                "color": self._color.name(), "width": self._width}

    @staticmethod
    def from_dict(d: dict) -> "EllipseDrawItem":
        item = EllipseDrawItem(QRectF(d["rx"], d["ry"], d["rw"], d["rh"]),
                               QColor(d["color"]), d["width"])
        item.setPos(d["x"], d["y"])
        return item


# ── Arrow ─────────────────────────────────────────────────────────────────────

class ArrowItem(QGraphicsPathItem):
    item_type = "arrow"

    def __init__(self, p1: QPointF, p2: QPointF,
                 color: QColor = DEFAULT_DRAW_COLOR, width: int = 2):
        super().__init__()
        self._color = color
        self._width = width
        self._p1, self._p2 = p1, p2
        self._rebuild()
        self.setFlags(_DRAW_FLAGS)
        self._handles = {"p1": _CornerHandle("p1", self), "p2": _CornerHandle("p2", self)}
        for h in self._handles.values(): h.setVisible(False)
        self._update_handles()

    def _update_handles(self):
        self._handles["p1"].setPos(self._p1)
        self._handles["p2"].setPos(self._p2)

    def _handle_drag(self, corner: str, delta: QPointF):
        if corner == "p1": self._p1 = self._p1 + delta
        else:              self._p2 = self._p2 + delta
        self._rebuild()
        self._update_handles()

    def _rebuild(self):
        p1, p2 = self._p1, self._p2
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        head, side = 14, 5
        lx = p2.x() - ux * head - uy * side
        ly = p2.y() - uy * head + ux * side
        rx = p2.x() - ux * head + uy * side
        ry = p2.y() - uy * head - ux * side
        path = QPainterPath(p1)
        path.lineTo(p2)
        path.moveTo(p2)
        path.lineTo(QPointF(lx, ly))
        path.lineTo(QPointF(rx, ry))
        path.lineTo(p2)
        self.setPath(path)
        self.setPen(QPen(self._color, self._width))
        self.setBrush(QBrush(self._color))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            _sync_handles(self)
        return super().itemChange(change, value)

    def to_dict(self) -> dict:
        p = self.pos()
        return {"item_type": "arrow", "x": p.x(), "y": p.y(),
                "x1": self._p1.x(), "y1": self._p1.y(),
                "x2": self._p2.x(), "y2": self._p2.y(),
                "color": self._color.name(), "width": self._width}

    @staticmethod
    def from_dict(d: dict) -> "ArrowItem":
        item = ArrowItem(QPointF(d["x1"], d["y1"]), QPointF(d["x2"], d["y2"]),
                         QColor(d["color"]), d["width"])
        item.setPos(d["x"], d["y"])
        return item


# ── Text label ────────────────────────────────────────────────────────────────

class TextLabelItem(QGraphicsTextItem):
    item_type = "text"

    def __init__(self, text: str, pos: QPointF, color: QColor = TEXT_COLOR,
                 bg_color: QColor | None = None, show_border: bool = False):
        super().__init__(text)
        self._color       = color
        self._bg_color    = bg_color
        self._show_border = show_border
        self.setDefaultTextColor(color)
        self.setFont(QFont("Segoe UI", 11))
        self.setPos(pos)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

    def _enter_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()
        cursor = self.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.setTextCursor(cursor)

    def _exit_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def mouseDoubleClickEvent(self, event):
        self._enter_edit()
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self._exit_edit()
        super().focusOutEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        r = self.boundingRect()
        if self._bg_color is not None:
            painter.setBrush(QBrush(self._bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(r, 4, 4)
        if self._show_border:
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.setPen(QPen(self._color, 1.5))
            painter.drawRoundedRect(r, 4, 4)
        super().paint(painter, option, widget)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            "item_type":   "text",
            "x": p.x(), "y": p.y(),
            "text":        self.toPlainText(),
            "color":       self._color.name(),
            "bg_color":    self._bg_color.name() if self._bg_color else None,
            "show_border": self._show_border,
        }

    @staticmethod
    def from_dict(d: dict) -> "TextLabelItem":
        bg = QColor(d["bg_color"]) if d.get("bg_color") else None
        return TextLabelItem(d["text"], QPointF(d["x"], d["y"]),
                             QColor(d["color"]), bg, d.get("show_border", False))


# ── Type group (used by scene / view) ─────────────────────────────────────────
DRAW_ITEM_TYPES = (StrokeItem, RectDrawItem, EllipseDrawItem, ArrowItem, TextLabelItem)
