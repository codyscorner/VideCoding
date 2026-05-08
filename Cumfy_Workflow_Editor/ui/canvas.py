from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene,
    QGraphicsProxyWidget, QGraphicsItem, QGraphicsPathItem,
)
from PyQt6.QtCore import Qt, QPointF, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush

from ui.node_cards import make_card
from ui.styles import COLORS
from workflow import WorkflowData


class NodeProxy(QGraphicsProxyWidget):
    """Proxy wrapper that emits a signal whenever the card is moved."""

    position_changed = pyqtSignal()

    def __init__(self, card):
        super().__init__()
        self.setWidget(card)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.position_changed.emit()
        return super().itemChange(change, value)


class ConnectionLine(QGraphicsPathItem):
    """Bezier curve linking two node proxies; updates live when either is moved."""

    def __init__(self, src: NodeProxy, dst: NodeProxy):
        super().__init__()
        self.src = src
        self.dst = dst

        pen = QPen(QColor(COLORS["border"]), 1.5)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setZValue(-1)  # render behind cards

        src.position_changed.connect(self._update)
        dst.position_changed.connect(self._update)
        self._update()

    def _update(self):
        sw = self.src.widget().width()  if self.src.widget() else 0
        sh = self.src.widget().height() if self.src.widget() else 0
        dh = self.dst.widget().height() if self.dst.widget() else 0

        sp = self.src.pos()
        dp = self.dst.pos()

        start = QPointF(sp.x() + sw, sp.y() + sh / 2)
        end   = QPointF(dp.x(),      dp.y() + dh / 2)

        ctrl = min(abs(end.x() - start.x()) * 0.5, 120.0)
        path = QPainterPath(start)
        path.cubicTo(
            start + QPointF(ctrl, 0),
            end   - QPointF(ctrl, 0),
            end,
        )
        self.setPath(path)


class WorkflowCanvas(QGraphicsView):
    workflow_modified = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_dark"])))

        self._pan_active = False
        self._pan_start = QPoint()
        self._proxies: dict[str, NodeProxy] = {}
        self._connections: list[ConnectionLine] = []

    # ── public API ────────────────────────────────────────────────────────

    def load_workflow(self, workflow: WorkflowData):
        self._scene.clear()
        self._proxies.clear()
        self._connections.clear()

        for node_id, node_data in workflow.nodes():
            card = make_card(node_id, node_data)
            card.data_changed.connect(self.workflow_modified)

            proxy = NodeProxy(card)
            self._scene.addItem(proxy)
            self._proxies[node_id] = proxy

        layout = workflow.load_layout() or workflow.auto_layout()
        for node_id, proxy in self._proxies.items():
            if node_id in layout:
                x, y = layout[node_id]
                proxy.setPos(x, y)

        self._draw_connections(workflow)

        rect = self._scene.itemsBoundingRect()
        if not rect.isEmpty():
            self.fitInView(rect.adjusted(-50, -50, 50, 50), Qt.AspectRatioMode.KeepAspectRatio)

    def get_positions(self) -> dict[str, tuple[float, float]]:
        return {nid: (p.pos().x(), p.pos().y()) for nid, p in self._proxies.items()}

    # ── internals ─────────────────────────────────────────────────────────

    def _draw_connections(self, workflow: WorkflowData):
        drawn: set[tuple[int, int]] = set()
        for node_id, node_data in workflow.nodes():
            dst = self._proxies.get(node_id)
            if dst is None:
                continue
            for val in node_data.get("inputs", {}).values():
                if isinstance(val, list) and len(val) == 2:
                    src = self._proxies.get(str(val[0]))
                    if src and src is not dst:
                        key = (id(src), id(dst))
                        if key not in drawn:
                            line = ConnectionLine(src, dst)
                            self._scene.addItem(line)
                            self._connections.append(line)
                            drawn.add(key)

    # ── mouse / wheel ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_active:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    # ── background grid ───────────────────────────────────────────────────

    def drawBackground(self, painter: QPainter, rect):
        super().drawBackground(painter, rect)
        grid = 30
        pen = QPen(QColor(COLORS["border"]), 0.4)
        painter.setPen(pen)

        left = int(rect.left())   - (int(rect.left())   % grid)
        top  = int(rect.top())    - (int(rect.top())    % grid)

        x = left
        while x < rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += grid
        y = top
        while y < rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += grid
