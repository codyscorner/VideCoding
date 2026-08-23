"""Programmatic toolbar icons, drawn with QPainter to match the dark theme.

make_icon(name) -> QIcon. All icons are drawn on a 32x32 canvas with the
theme's light stroke color so they stay crisp at any toolbar size.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QFont, QIcon, QPainter, QPainterPath,
                         QPen, QPixmap, QPolygonF)

STROKE = QColor("#d7e8dd")
ACCENT = QColor("#3fa46a")
YELLOW = QColor("#ffd400")


def _pen(w=2.2, color=None):
    p = QPen(color or STROKE, w)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def _text(p, s, size=17, color=None, rect=QRectF(4, 4, 24, 24)):
    f = QFont("Segoe UI", size)
    f.setBold(True)
    p.setFont(f)
    p.setPen(_pen(2, color))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, s)


def _arrowhead(p, tip: QPointF, back: QPointF, size=5.0):
    d = QPointF(tip.x() - back.x(), tip.y() - back.y())
    ln = max(1e-6, (d.x() ** 2 + d.y() ** 2) ** 0.5)
    ux, uy = d.x() / ln, d.y() / ln
    px, py = -uy, ux
    a = QPointF(tip.x() - ux * size + px * size * .7,
                tip.y() - uy * size + py * size * .7)
    b = QPointF(tip.x() - ux * size - px * size * .7,
                tip.y() - uy * size - py * size * .7)
    p.setBrush(QBrush(p.pen().color()))
    p.drawPolygon(QPolygonF([tip, a, b]))


def _draw(name: str, p: QPainter):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(_pen())
    p.setBrush(Qt.BrushStyle.NoBrush)

    if name == "select":
        p.setBrush(QBrush(STROKE))
        p.drawPolygon(QPolygonF([QPointF(9, 4), QPointF(9, 24), QPointF(14, 19),
                                 QPointF(18, 27), QPointF(21, 25),
                                 QPointF(17, 17), QPointF(24, 17)]))
    elif name == "open":
        p.drawPolygon(QPolygonF([QPointF(4, 9), QPointF(12, 9), QPointF(14, 12),
                                 QPointF(28, 12), QPointF(28, 26), QPointF(4, 26)]))
        p.setPen(_pen(2, ACCENT))
        p.drawLine(QPointF(8, 17), QPointF(24, 17))
    elif name == "save":
        p.drawRoundedRect(QRectF(5, 5, 22, 22), 2, 2)
        p.drawRect(QRectF(11, 5, 10, 8))
        p.fillRect(QRectF(10, 17, 12, 10), ACCENT)
    elif name == "undo":
        path = QPainterPath(QPointF(9, 12))
        path.cubicTo(QPointF(20, 4), QPointF(28, 12), QPointF(24, 24))
        p.drawPath(path)
        _arrowhead(p, QPointF(8, 13), QPointF(14, 8))
    elif name == "redo":
        path = QPainterPath(QPointF(23, 12))
        path.cubicTo(QPointF(12, 4), QPointF(4, 12), QPointF(8, 24))
        p.drawPath(path)
        _arrowhead(p, QPointF(24, 13), QPointF(18, 8))
    elif name == "pan":
        p.drawLine(QPointF(16, 5), QPointF(16, 27))
        p.drawLine(QPointF(5, 16), QPointF(27, 16))
        for tip, back in [((16, 4), (16, 10)), ((16, 28), (16, 22)),
                          ((4, 16), (10, 16)), ((28, 16), (22, 16))]:
            _arrowhead(p, QPointF(*tip), QPointF(*back), 4)
    elif name == "highlight":
        p.fillRect(QRectF(5, 12, 22, 10), QColor(255, 212, 0, 110))
        p.setPen(_pen(2, YELLOW))
        p.drawRect(QRectF(5, 12, 22, 10))
    elif name == "underline":
        _text(p, "U", rect=QRectF(4, 2, 24, 22))
        p.setPen(_pen(2.4, ACCENT))
        p.drawLine(QPointF(8, 27), QPointF(24, 27))
    elif name == "strikeout":
        _text(p, "S", rect=QRectF(4, 4, 24, 24))
        p.setPen(_pen(2.4, ACCENT))
        p.drawLine(QPointF(6, 16), QPointF(26, 16))
    elif name == "pen":
        p.drawPolygon(QPolygonF([QPointF(6, 26), QPointF(8, 20), QPointF(22, 6),
                                 QPointF(26, 10), QPointF(12, 24)]))
        p.fillRect(QRectF(6, 24, 4, 3), ACCENT)
    elif name == "rect":
        p.drawRect(QRectF(5, 8, 22, 16))
    elif name == "ellipse":
        p.drawEllipse(QRectF(5, 8, 22, 16))
    elif name == "line":
        p.drawLine(QPointF(6, 26), QPointF(26, 6))
    elif name == "arrow":
        p.drawLine(QPointF(6, 26), QPointF(24, 8))
        _arrowhead(p, QPointF(26, 6), QPointF(18, 14))
    elif name == "textbox":
        p.drawRect(QRectF(4, 7, 24, 18))
        _text(p, "T", 13, rect=QRectF(4, 7, 24, 18))
    elif name == "note":
        p.drawPolygon(QPolygonF([QPointF(6, 5), QPointF(26, 5), QPointF(26, 21),
                                 QPointF(20, 21), QPointF(14, 27), QPointF(14, 21),
                                 QPointF(6, 21)]))
        p.setPen(_pen(2, ACCENT))
        p.drawLine(QPointF(10, 11), QPointF(22, 11))
        p.drawLine(QPointF(10, 15), QPointF(18, 15))
    elif name == "eraser":
        p.save()
        p.translate(16, 16)
        p.rotate(-35)
        p.drawRoundedRect(QRectF(-10, -6, 20, 12), 2, 2)
        p.fillRect(QRectF(2, -6, 8, 12), ACCENT)
        p.restore()
    elif name == "redact":
        p.fillRect(QRectF(5, 10, 22, 12), QColor(10, 10, 10))
        p.drawRect(QRectF(5, 10, 22, 12))
    elif name == "crossout":
        r = QRectF(5, 9, 22, 14)
        p.setPen(_pen(2, QColor("#d05050")))
        p.drawRect(r)
        p.drawLine(r.topLeft(), r.bottomRight())
        p.drawLine(r.topRight(), r.bottomLeft())
    elif name == "callout":
        p.drawRoundedRect(QRectF(10, 4, 18, 13), 3, 3)
        p.setPen(_pen(2, ACCENT))
        p.drawLine(QPointF(15, 9), QPointF(23, 9))
        p.setPen(_pen())
        p.drawLine(QPointF(13, 17), QPointF(5, 27))
        _arrowhead(p, QPointF(4, 28), QPointF(10, 21), 4)
    elif name in ("rotate_l", "rotate_r"):
        path = QPainterPath()
        if name == "rotate_l":
            path.moveTo(QPointF(9, 10))
            path.cubicTo(QPointF(18, 2), QPointF(28, 8), QPointF(26, 19))
            p.drawPath(path)
            _arrowhead(p, QPointF(8, 11), QPointF(14, 6))
        else:
            path.moveTo(QPointF(23, 10))
            path.cubicTo(QPointF(14, 2), QPointF(4, 8), QPointF(6, 19))
            p.drawPath(path)
            _arrowhead(p, QPointF(24, 11), QPointF(18, 6))
        p.drawRect(QRectF(11, 18, 10, 9))
    elif name in ("zoom_in", "zoom_out"):
        p.drawEllipse(QRectF(5, 5, 15, 15))
        p.drawLine(QPointF(18, 18), QPointF(27, 27))
        p.drawLine(QPointF(9, 12.5), QPointF(16, 12.5))
        if name == "zoom_in":
            p.drawLine(QPointF(12.5, 9), QPointF(12.5, 16))
    elif name == "fit_width":
        p.drawLine(QPointF(4, 6), QPointF(4, 26))
        p.drawLine(QPointF(28, 6), QPointF(28, 26))
        p.drawLine(QPointF(8, 16), QPointF(24, 16))
        _arrowhead(p, QPointF(7, 16), QPointF(13, 16), 4)
        _arrowhead(p, QPointF(25, 16), QPointF(19, 16), 4)
    elif name == "fit_page":
        p.drawRect(QRectF(8, 4, 16, 24))
        p.setPen(_pen(1.8, ACCENT))
        p.drawLine(QPointF(12, 10), QPointF(20, 10))
        p.drawLine(QPointF(12, 16), QPointF(20, 16))
        p.drawLine(QPointF(12, 22), QPointF(20, 22))
    elif name == "prev":
        p.setBrush(QBrush(STROKE))
        p.drawPolygon(QPolygonF([QPointF(20, 6), QPointF(20, 26), QPointF(9, 16)]))
    elif name == "next":
        p.setBrush(QBrush(STROKE))
        p.drawPolygon(QPolygonF([QPointF(12, 6), QPointF(12, 26), QPointF(23, 16)]))


def make_icon(name: str) -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    _draw(name, p)
    p.end()
    return QIcon(pm)
