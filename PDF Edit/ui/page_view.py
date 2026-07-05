"""Main page view: renders one page and hosts all markup tools.

All model coordinates are unrotated PDF space; conversion happens only
through transform.PageTransform (see that module's docstring).
"""

from enum import Enum, auto

import fitz
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QInputDialog, QToolTip, QWidget

from document import HIGHLIGHT, STRIKEOUT, UNDERLINE, PdfDocument
from ui.callout_dialog import TextAnnotDialog
from transform import PageTransform


class Tool(Enum):
    SELECT = auto()
    PAN = auto()
    HIGHLIGHT = auto()
    UNDERLINE = auto()
    STRIKEOUT = auto()
    PEN = auto()
    RECT = auto()
    ELLIPSE = auto()
    LINE = auto()
    ARROW = auto()
    TEXTBOX = auto()
    NOTE = auto()
    ERASER = auto()
    REDACT = auto()
    CROSSOUT = auto()
    CALLOUT = auto()

# Highlight is a drag-box (works on scans with no text layer);
# underline/strikeout stay text-selection based.
TEXT_TOOLS = {Tool.UNDERLINE: UNDERLINE, Tool.STRIKEOUT: STRIKEOUT}
DRAG_SHAPE_TOOLS = {Tool.HIGHLIGHT, Tool.RECT, Tool.ELLIPSE, Tool.LINE,
                    Tool.ARROW, Tool.REDACT, Tool.CROSSOUT, Tool.CALLOUT}
HIGHLIGHT_OPACITY = 0.3

WORD_HIT_TOL_PX = 4  # hit tolerance around word rects, in screen pixels


class PageView(QWidget):
    documentChanged = pyqtSignal()          # any annotation added/removed
    statusMessage = pyqtSignal(str)
    zoomChanged = pyqtSignal(float)

    def __init__(self, scroll_area, parent=None):
        super().__init__(parent)
        self._scroll = scroll_area
        self.pdf: PdfDocument | None = None
        self.pno = 0
        self.zoom = 1.0
        self.tool = Tool.PAN
        self.color = QColor("#ffd400")      # classic highlighter yellow
        self.pen_width = 2.0

        self._qimage: QImage | None = None
        self._tx: PageTransform | None = None

        # interaction state
        self._pan_last = None
        self._ink_pts: list[fitz.Point] = []
        self._drag_start: QPointF | None = None
        self._drag_cur: QPointF | None = None
        self._sel_order: list[int] = []     # word indices in reading order
        self._sel_anchor: int | None = None  # position in _sel_order
        self._sel_current: int | None = None
        self._search_rects: list[fitz.Rect] = []
        self._search_active: fitz.Rect | None = None

        # selection (Select tool)
        self._sel_xref: int | None = None
        self._sel_rect: fitz.Rect | None = None
        self._sel_type: str = ""
        self._move_start: QPointF | None = None
        self._move_cur: QPointF | None = None

        self.setMouseTracking(True)   # hover tooltips for comments
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._hover_xref: int | None = None

    # ------------------------------------------------------------- document

    def set_document(self, pdf: PdfDocument):
        self.pdf = pdf
        self.pno = 0
        self.render_page()

    def set_page(self, pno: int):
        if not self.pdf or not self.pdf.is_open:
            return
        self.pno = max(0, min(pno, self.pdf.page_count - 1))
        self._reset_interaction()
        self.render_page()

    def set_search_results(self, rects: list[fitz.Rect],
                           active: fitz.Rect | None):
        self._search_rects = rects
        self._search_active = active
        self.update()

    def render_page(self):
        if not self.pdf or not self.pdf.is_open:
            self._qimage = None
            self._tx = None
            self.setFixedSize(400, 300)
            self.update()
            return
        page = self.pdf.doc[self.pno]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom),
                              alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                     QImage.Format.Format_RGB888)
        self._qimage = img.copy()  # detach from pix buffer before pix dies
        self._tx = PageTransform(page, self.zoom)
        self._note_rects = self.pdf.note_rects(self.pno)
        self.setFixedSize(pix.width, pix.height)
        self.update()

    # ------------------------------------------------------------- zoom

    def set_zoom(self, zoom: float):
        self.zoom = max(0.1, min(zoom, 8.0))
        self.render_page()
        self.zoomChanged.emit(self.zoom)

    def zoom_in(self):
        self.set_zoom(self.zoom * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom / 1.25)

    def fit_width(self):
        if not self.pdf or not self.pdf.is_open:
            return
        page = self.pdf.doc[self.pno]
        avail = self._scroll.viewport().width() - 4
        if page.rect.width > 0:
            self.set_zoom(avail / page.rect.width)

    def fit_page(self):
        if not self.pdf or not self.pdf.is_open:
            return
        page = self.pdf.doc[self.pno]
        vp = self._scroll.viewport()
        if page.rect.width > 0 and page.rect.height > 0:
            self.set_zoom(min((vp.width() - 4) / page.rect.width,
                              (vp.height() - 4) / page.rect.height))

    def wheelEvent(self, ev):
        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in() if ev.angleDelta().y() > 0 else self.zoom_out()
            ev.accept()
        else:
            ev.ignore()  # let the scroll area scroll

    # ------------------------------------------------------------- tools

    def set_tool(self, tool: Tool):
        self.tool = tool
        self._reset_interaction()
        cursors = {
            Tool.SELECT: Qt.CursorShape.ArrowCursor,
            Tool.PAN: Qt.CursorShape.OpenHandCursor,
            Tool.ERASER: Qt.CursorShape.PointingHandCursor,
            Tool.TEXTBOX: Qt.CursorShape.IBeamCursor,
            Tool.NOTE: Qt.CursorShape.PointingHandCursor,
        }
        if tool in TEXT_TOOLS:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self.setCursor(cursors.get(tool, Qt.CursorShape.CrossCursor))
        self.update()

    def _reset_interaction(self):
        self._pan_last = None
        self._ink_pts = []
        self._drag_start = self._drag_cur = None
        self._sel_anchor = self._sel_current = None
        self._sel_order = []
        self._sel_xref = self._sel_rect = None
        self._sel_type = ""
        self._move_start = self._move_cur = None

    def _fitz_color(self) -> tuple:
        return (self.color.redF(), self.color.greenF(), self.color.blueF())

    # ------------------------------------------------------------- words

    def _load_words(self) -> bool:
        """Prepare reading-order word index for the current page."""
        words = self.pdf.words(self.pno)
        if not words:
            self.statusMessage.emit(
                "No selectable text on this page (scanned image?)")
            return False
        self._sel_order = sorted(
            range(len(words)),
            key=lambda i: (words[i][5], words[i][6], words[i][7]))
        return True

    def _word_at(self, pdf_pt: fitz.Point, must_hit: bool) -> int | None:
        """Position in _sel_order of the word at/nearest pdf_pt."""
        words = self.pdf.words(self.pno)
        tol = self._tx.px_to_pdf_len(WORD_HIT_TOL_PX)
        best, best_d = None, None
        for pos, i in enumerate(self._sel_order):
            r = fitz.Rect(words[i][:4])
            rr = fitz.Rect(r.x0 - tol, r.y0 - tol, r.x1 + tol, r.y1 + tol)
            if rr.contains(pdf_pt):
                return pos
            if not must_hit:
                cx = max(r.x0, min(pdf_pt.x, r.x1))
                cy = max(r.y0, min(pdf_pt.y, r.y1))
                d = (cx - pdf_pt.x) ** 2 + (cy - pdf_pt.y) ** 2
                if best_d is None or d < best_d:
                    best, best_d = pos, d
        return best

    def _selected_line_rects(self) -> list[fitz.Rect]:
        """Merge the selected word range into one rect per text line."""
        if self._sel_anchor is None or self._sel_current is None:
            return []
        words = self.pdf.words(self.pno)
        lo = min(self._sel_anchor, self._sel_current)
        hi = max(self._sel_anchor, self._sel_current)
        rows: dict[tuple, fitz.Rect] = {}
        for pos in range(lo, hi + 1):
            w = words[self._sel_order[pos]]
            key = (w[5], w[6])
            r = fitz.Rect(w[:4])
            if key in rows:
                rows[key].include_rect(r)
            else:
                rows[key] = r
        return [rows[k] for k in sorted(rows)]

    # ------------------------------------------------------------- mouse

    def mousePressEvent(self, ev):
        if (ev.button() != Qt.MouseButton.LeftButton or not self.pdf
                or not self.pdf.is_open or self._tx is None):
            return
        pos = ev.position()
        pdf_pt = self._tx.to_pdf(pos)

        if self.tool == Tool.SELECT:
            hit = self.pdf.annot_at(self.pno, pdf_pt,
                                    tol=self._tx.px_to_pdf_len(WORD_HIT_TOL_PX))
            if hit:
                self._sel_xref, self._sel_rect, self._sel_type = hit[:3]
                self._move_start = self._move_cur = pos
                self.statusMessage.emit(
                    f"{self._sel_type} selected — drag to move, "
                    "Del to delete" + (", double-click to edit text"
                                       if self._sel_type == "FreeText" else ""))
            else:
                self._sel_xref = self._sel_rect = None
                self._sel_type = ""
            self.update()

        elif self.tool == Tool.PAN:
            self._pan_last = ev.globalPosition()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        elif self.tool in TEXT_TOOLS:
            if self._load_words():
                self._sel_anchor = self._word_at(pdf_pt, must_hit=True)
                self._sel_current = self._sel_anchor

        elif self.tool == Tool.PEN:
            self._ink_pts = [pdf_pt]

        elif self.tool in DRAG_SHAPE_TOOLS:
            self._drag_start = self._drag_cur = pos

        elif self.tool == Tool.TEXTBOX:
            self._place_textbox(pdf_pt)

        elif self.tool == Tool.NOTE:
            self._place_note(pdf_pt)

        elif self.tool == Tool.ERASER:
            tol = self._tx.px_to_pdf_len(WORD_HIT_TOL_PX)
            if self.pdf.delete_annot_at(self.pno, pdf_pt, tol=tol):
                self.render_page()
                self.documentChanged.emit()
                self.statusMessage.emit("Annotation deleted")
            else:
                self.statusMessage.emit("No annotation here")

    def mouseMoveEvent(self, ev):
        if self._tx is None:
            return
        pos = ev.position()

        # hover (no buttons): show comment tooltips with Select/Pan tools
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            if (self.tool in (Tool.SELECT, Tool.PAN) and self.pdf
                    and self.pdf.is_open):
                hit = self.pdf.annot_at(
                    self.pno, self._tx.to_pdf(pos),
                    tol=self._tx.px_to_pdf_len(WORD_HIT_TOL_PX))
                if hit and hit[3]:
                    if hit[0] != self._hover_xref:
                        self._hover_xref = hit[0]
                        QToolTip.showText(ev.globalPosition().toPoint(),
                                          hit[3], self)
                else:
                    self._hover_xref = None
                    QToolTip.hideText()
            return

        if self.tool == Tool.SELECT and self._move_start is not None:
            self._move_cur = pos
            self.update()

        elif self.tool == Tool.PAN and self._pan_last is not None:
            delta = ev.globalPosition() - self._pan_last
            self._pan_last = ev.globalPosition()
            h = self._scroll.horizontalScrollBar()
            v = self._scroll.verticalScrollBar()
            h.setValue(h.value() - int(delta.x()))
            v.setValue(v.value() - int(delta.y()))

        elif self.tool in TEXT_TOOLS and self._sel_anchor is not None:
            self._sel_current = self._word_at(self._tx.to_pdf(pos),
                                              must_hit=False)
            self.update()

        elif self.tool == Tool.PEN and self._ink_pts:
            self._ink_pts.append(self._tx.to_pdf(pos))
            self.update()

        elif self.tool in DRAG_SHAPE_TOOLS and self._drag_start is not None:
            self._drag_cur = pos
            self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton or self._tx is None:
            return

        if self.tool == Tool.SELECT:
            if (self._sel_xref is not None and self._move_start is not None
                    and self._move_cur is not None
                    and (self._move_cur - self._move_start).manhattanLength() > 3):
                d = (self._tx.to_pdf(self._move_cur)
                     - self._tx.to_pdf(self._move_start))
                self.pdf.move_annot(self.pno, self._sel_xref, d.x, d.y)
                self._sel_rect = fitz.Rect(self._sel_rect) + (d.x, d.y,
                                                              d.x, d.y)
                self._commit()
            self._move_start = self._move_cur = None
            self.update()

        elif self.tool == Tool.PAN:
            self._pan_last = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

        elif self.tool in TEXT_TOOLS:
            rects = self._selected_line_rects()
            if rects:
                self.pdf.add_text_markup(self.pno, rects,
                                         TEXT_TOOLS[self.tool],
                                         self._fitz_color())
                self._commit()
            self._sel_anchor = self._sel_current = None
            self.update()

        elif self.tool == Tool.PEN:
            if len(self._ink_pts) > 1:
                self.pdf.add_ink(self.pno, self._ink_pts, self._fitz_color(),
                                 self.pen_width)
                self._commit()
            self._ink_pts = []

        elif self.tool in DRAG_SHAPE_TOOLS and self._drag_start is not None:
            self._finish_drag_shape()

    def mouseDoubleClickEvent(self, ev):
        if (self.tool != Tool.SELECT or self._tx is None
                or ev.button() != Qt.MouseButton.LeftButton):
            return
        hit = self.pdf.annot_at(self.pno, self._tx.to_pdf(ev.position()),
                                tol=self._tx.px_to_pdf_len(WORD_HIT_TOL_PX))
        if not hit:
            return
        if hit[2] == "Text":  # sticky note: edit the comment text
            text, ok = QInputDialog.getMultiLineText(
                self, "Edit Note", "Note:", hit[3])
            if ok and text.strip():
                self.pdf.update_note(self.pno, hit[0], text)
                self._commit()
            return
        if hit[2] != "FreeText":
            return
        xref = hit[0]
        info = self.pdf.freetext_info(self.pno, xref)
        if info is None:
            return
        dlg = TextAnnotDialog(
            self, "Edit Callout" if info["target"] else "Edit Text Box")
        dlg.edit.setPlainText(info["text"])
        if dlg.exec() != dlg.DialogCode.Accepted or not dlg.text:
            return
        fs = dlg.fontsize * self.pdf.page_scale(self.pno)
        bubble = info["bubble"]
        rect = self._text_rect_for(dlg.text, fs,
                                   fitz.Point(bubble.x0, bubble.y0))
        self.pdf.replace_freetext(self.pno, xref, rect, dlg.text,
                                  dlg.rgb_text(), dlg.rgb_fill(), fs,
                                  dlg.fontname, info["target"],
                                  border_width=self.pen_width)
        self._sel_xref = self._sel_rect = None
        self._commit()

    def keyPressEvent(self, ev):
        if (ev.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
                and self.tool == Tool.SELECT and self._sel_xref is not None):
            self.pdf.delete_annot_by_xref(self.pno, self._sel_xref)
            self._sel_xref = self._sel_rect = None
            self._commit()
            self.statusMessage.emit("Annotation deleted")
        else:
            super().keyPressEvent(ev)

    def _finish_drag_shape(self):
        a, b = self._drag_start, self._drag_cur
        self._drag_start = self._drag_cur = None
        if a is None or b is None or (a - b).manhattanLength() < 5:
            self.update()
            return
        if self.tool == Tool.CALLOUT:
            self._place_callout(self._tx.to_pdf(a), self._tx.to_pdf(b))
        elif self.tool in (Tool.LINE, Tool.ARROW):
            self.pdf.add_line(self.pno, self._tx.to_pdf(a), self._tx.to_pdf(b),
                              self._fitz_color(), self.pen_width,
                              arrow=self.tool == Tool.ARROW)
        else:
            rect = self._tx.rect_to_pdf(QRectF(a, b).normalized())
            if self.tool == Tool.REDACT:
                self.pdf.redact_area(self.pno, rect)
                self.statusMessage.emit(
                    "Area redacted — content removed (Ctrl+Z to undo)")
            elif self.tool == Tool.HIGHLIGHT:
                self.pdf.add_highlight_box(self.pno, rect, self._fitz_color(),
                                           HIGHLIGHT_OPACITY)
            elif self.tool == Tool.CROSSOUT:
                self.pdf.add_crossout_box(self.pno, rect, self._fitz_color(),
                                          self.pen_width)
            else:
                kind = "rect" if self.tool == Tool.RECT else "ellipse"
                self.pdf.add_shape(self.pno, kind, rect, self._fitz_color(),
                                   self.pen_width)
        self._commit()

    def _text_rect_for(self, text: str, fs: float, at: fitz.Point) -> fitz.Rect:
        """Auto-size a text rect at `at`, clamped to the page."""
        lines = text.split("\n")
        w = max(60.0, max(len(ln) for ln in lines) * fs * 0.62 + 12)
        h = max(fs * 1.6, len(lines) * fs * 1.45 + 8)
        page_rect = self.pdf.doc[self.pno].rect
        x0 = max(0.0, min(at.x, page_rect.width - w))
        y0 = max(0.0, min(at.y, page_rect.height - h))
        return fitz.Rect(x0, y0, x0 + w, y0 + h)

    def _place_callout(self, target: fitz.Point, bubble_at: fitz.Point):
        dlg = TextAnnotDialog(self, "Callout")
        if dlg.exec() != dlg.DialogCode.Accepted or not dlg.text:
            self.update()
            return
        # dialog font size is in visual points; scale to hi-DPI page units
        fs = dlg.fontsize * self.pdf.page_scale(self.pno)
        rect = self._text_rect_for(dlg.text, fs, bubble_at)
        self.pdf.add_callout(self.pno, target, rect, dlg.text,
                             dlg.rgb_text(), dlg.rgb_fill(), fontsize=fs,
                             border_width=self.pen_width,
                             fontname=dlg.fontname)
        self._commit()

    def _place_textbox(self, pdf_pt: fitz.Point):
        dlg = TextAnnotDialog(self, "Text Box")
        if dlg.exec() != dlg.DialogCode.Accepted or not dlg.text:
            return
        fs = dlg.fontsize * self.pdf.page_scale(self.pno)
        rect = self._text_rect_for(dlg.text, fs, pdf_pt)
        self.pdf.add_textbox(self.pno, rect, dlg.text, dlg.rgb_text(),
                             dlg.rgb_fill(), fontsize=fs,
                             fontname=dlg.fontname)
        self._commit()

    def _place_note(self, pdf_pt: fitz.Point):
        text, ok = QInputDialog.getMultiLineText(self, "Sticky Note", "Note:")
        if not ok or not text.strip():
            return
        self.pdf.add_note(self.pno, pdf_pt, text)
        self._commit()

    def _commit(self):
        self.render_page()
        self.documentChanged.emit()

    # ------------------------------------------------------------- painting

    def paintEvent(self, ev):
        p = QPainter(self)
        if self._qimage is None:
            p.fillRect(self.rect(), QColor("#0e1813"))
            p.setPen(QColor("#8fae9c"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Open a PDF or drop one here")
            return
        p.drawImage(0, 0, self._qimage)

        # search hits
        for r in self._search_rects:
            vr = self._tx.rect_to_view(r)
            active = (self._search_active is not None
                      and fitz.Rect(r) == fitz.Rect(self._search_active))
            p.fillRect(vr, QColor(63, 164, 106, 130 if active else 60))
            if active:
                p.setPen(QPen(QColor("#3fa46a"), 2))
                p.drawRect(vr)

        # sticky-note markers (fixed screen size; PDF icon is tiny on scans)
        for r in getattr(self, "_note_rects", []):
            at = self._tx.to_view(fitz.Point(r.x0, r.y0))
            box = QRectF(at.x(), at.y(), 22, 22)
            p.setPen(QPen(QColor("#8a6d00"), 1.5))
            p.setBrush(QColor("#ffd400"))
            p.drawRoundedRect(box, 3, 3)
            p.setPen(QPen(QColor("#5a4700"), 1.5))
            p.drawLine(QPointF(at.x() + 5, at.y() + 8),
                       QPointF(at.x() + 17, at.y() + 8))
            p.drawLine(QPointF(at.x() + 5, at.y() + 13),
                       QPointF(at.x() + 14, at.y() + 13))
            p.setBrush(Qt.BrushStyle.NoBrush)

        # selected annotation outline (Select tool)
        if self.tool == Tool.SELECT and self._sel_rect is not None:
            vr = self._tx.rect_to_view(self._sel_rect)
            if self._move_start is not None and self._move_cur is not None:
                off = self._move_cur - self._move_start
                vr.translate(off.x(), off.y())
            pen = QPen(QColor("#3fa46a"), 1.6, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(vr)

        # live text selection
        if self.tool in TEXT_TOOLS:
            for r in self._selected_line_rects():
                p.fillRect(self._tx.rect_to_view(r),
                           QColor(self.color.red(), self.color.green(),
                                  self.color.blue(), 90))

        # live ink stroke
        if self._ink_pts:
            pen = QPen(self.color, self.pen_width * self.zoom)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawPolyline(QPolygonF(
                [self._tx.to_view(pt) for pt in self._ink_pts]))

        # live drag shape
        if self._drag_start is not None and self._drag_cur is not None:
            if self.tool == Tool.REDACT:
                pen = QPen(QColor("#d33"), 1.5, Qt.PenStyle.DashLine)
            else:
                pen = QPen(self.color, max(1.0, self.pen_width * self.zoom))
            p.setPen(pen)
            rect = QRectF(self._drag_start, self._drag_cur).normalized()
            if self.tool == Tool.HIGHLIGHT:
                p.fillRect(rect, QColor(self.color.red(), self.color.green(),
                                        self.color.blue(),
                                        int(HIGHLIGHT_OPACITY * 255)))
            elif self.tool == Tool.RECT:
                p.drawRect(rect)
            elif self.tool == Tool.CROSSOUT:
                p.drawRect(rect)
                p.drawLine(rect.topLeft(), rect.bottomRight())
                p.drawLine(rect.topRight(), rect.bottomLeft())
            elif self.tool == Tool.CALLOUT:
                # tail from target (press) to bubble position (cursor)
                p.drawLine(self._drag_start, self._drag_cur)
                p.drawRect(QRectF(self._drag_cur.x(), self._drag_cur.y(),
                                  100, 36))
            elif self.tool == Tool.ELLIPSE:
                p.drawEllipse(rect)
            elif self.tool == Tool.REDACT:
                p.fillRect(rect, QColor(0, 0, 0, 120))
                p.drawRect(rect)
            else:
                p.drawLine(self._drag_start, self._drag_cur)
