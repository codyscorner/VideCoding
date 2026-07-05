"""Single owner of the mapping between PDF page space and rendered pixels.

Conventions (verified against PyMuPDF 1.28 for rotations 0/90/180/270):
- Pixmaps are rendered with page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)),
  which ALREADY applies page /Rotate.
- Text extraction, search_for and annotation coordinates are in UNROTATED
  page space.
- page.rotation_matrix maps unrotated space -> rotated (displayed) space.
- No Y-flip: PyMuPDF and Qt both use a top-left origin.

Therefore: view = pdf_point * (rotation_matrix * Matrix(zoom, zoom)),
and the inverse maps mouse positions back. Nothing else in the app may
do coordinate math on its own.
"""

import fitz
from PyQt6.QtCore import QPointF, QRectF


class PageTransform:
    def __init__(self, page: fitz.Page, zoom: float):
        self.zoom = zoom
        self.mat = page.rotation_matrix * fitz.Matrix(zoom, zoom)
        self.inv = ~self.mat

    def to_view(self, p: fitz.Point) -> QPointF:
        q = fitz.Point(p) * self.mat
        return QPointF(q.x, q.y)

    def to_pdf(self, pos) -> fitz.Point:
        """pos: QPoint/QPointF in widget pixels -> unrotated PDF point."""
        return fitz.Point(pos.x(), pos.y()) * self.inv

    def rect_to_view(self, r: fitz.Rect) -> QRectF:
        q = fitz.Rect(r) * self.mat
        q.normalize()
        return QRectF(q.x0, q.y0, q.width, q.height)

    def rect_to_pdf(self, r: QRectF) -> fitz.Rect:
        q = fitz.Rect(r.left(), r.top(), r.right(), r.bottom()) * self.inv
        q.normalize()
        return q

    def px_to_pdf_len(self, px: float) -> float:
        """Convert a pixel length (e.g. hit tolerance) to PDF units."""
        return px / self.zoom
