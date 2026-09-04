"""PDF document model: wraps fitz.Document with snapshot-based undo/redo.

All coordinates passed in and out of this module are in UNROTATED PDF page
space (the PyMuPDF convention for text extraction, search and annotations).
View widgets convert via transform.PageTransform.
"""

import os

import fitz

MAX_PAGES = 200      # hard cap — refuse to open/insert beyond this
MAX_UNDO = 25        # snapshot stack depth

HIGHLIGHT = "highlight"
UNDERLINE = "underline"
STRIKEOUT = "strikeout"


class PdfError(Exception):
    """User-presentable document error."""


class PdfDocument:
    def __init__(self):
        self.doc: fitz.Document | None = None
        self.path: str | None = None
        self.modified = False
        self._undo: list[bytes] = []
        self._redo: list[bytes] = []
        self._words: dict[int, list] = {}

    # ------------------------------------------------------------- lifecycle

    @property
    def is_open(self) -> bool:
        return self.doc is not None

    @property
    def page_count(self) -> int:
        return self.doc.page_count if self.doc else 0

    def open(self, path: str):
        try:
            doc = fitz.open(path)
        except Exception as e:
            raise PdfError(f"Could not open file:\n{e}") from e
        if not doc.is_pdf:
            doc.close()
            raise PdfError("Not a PDF file.")
        if doc.needs_pass:
            doc.close()
            raise PdfError("Password-protected PDFs are not supported.")
        if doc.page_count > MAX_PAGES:
            n = doc.page_count
            doc.close()
            raise PdfError(f"This PDF has {n} pages — the limit is {MAX_PAGES} pages.")
        if doc.page_count == 0:
            doc.close()
            raise PdfError("PDF contains no pages.")
        self.close()
        self.doc = doc
        self.path = path

    def close(self):
        if self.doc:
            self.doc.close()
        self.doc = None
        self.path = None
        self.modified = False
        self._undo.clear()
        self._redo.clear()
        self._words.clear()

    def to_bytes(self) -> bytes:
        return self.doc.tobytes()

    def save_as(self, path: str):
        if self.path and os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            os.path.abspath(self.path)
        ):
            # fitz keeps the source file open — serialize, release, rewrite, reopen
            data = self.doc.tobytes(garbage=3, deflate=True)
            self.doc.close()
            with open(path, "wb") as f:
                f.write(data)
            self.doc = fitz.open(path)
        else:
            self.doc.save(path, garbage=3, deflate=True)
            self.path = path
        self.modified = False

    def export_flattened(self, path: str):
        """Save a copy with annotations baked into page content."""
        copy = fitz.open("pdf", self.doc.tobytes())
        try:
            copy.bake(annots=True, widgets=True)
            copy.save(path, garbage=3, deflate=True)
        finally:
            copy.close()

    def split_to_folder(self, folder: str) -> int:
        stem = os.path.splitext(os.path.basename(self.path or "document"))[0]
        for i in range(self.doc.page_count):
            single = fitz.open()
            single.insert_pdf(self.doc, from_page=i, to_page=i)
            single.save(os.path.join(folder, f"{stem}_page_{i + 1:03d}.pdf"))
            single.close()
        return self.doc.page_count

    # ------------------------------------------------------------- undo/redo

    def _snapshot(self):
        self._undo.append(self.doc.tobytes())
        del self._undo[:-MAX_UNDO]
        self._redo.clear()
        self._words.clear()
        self.modified = True

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.doc.tobytes())
        self._reload(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.doc.tobytes())
        self._reload(self._redo.pop())
        return True

    def _reload(self, data: bytes):
        self.doc.close()
        self.doc = fitz.open("pdf", data)
        self._words.clear()
        self.modified = True

    # ------------------------------------------------------------- text

    def words(self, pno: int) -> list:
        """Cached word list: (x0, y0, x1, y1, word, block_no, line_no, word_no)."""
        if pno not in self._words:
            self._words[pno] = self.doc[pno].get_text("words")
        return self._words[pno]

    def search(self, text: str) -> list[tuple[int, fitz.Rect]]:
        hits = []
        for pno in range(self.doc.page_count):
            for r in self.doc[pno].search_for(text):
                hits.append((pno, r))
        return hits

    # ------------------------------------------------------------- page ops

    def delete_page(self, pno: int):
        if self.doc.page_count <= 1:
            raise PdfError("Cannot delete the only page.")
        self._snapshot()
        self.doc.delete_page(pno)

    def rotate_page(self, pno: int, delta: int):
        self._snapshot()
        page = self.doc[pno]
        page.set_rotation((page.rotation + delta) % 360)

    def duplicate_page(self, pno: int):
        if self.doc.page_count + 1 > MAX_PAGES:
            raise PdfError(f"Duplicating would exceed the {MAX_PAGES}-page limit.")
        self._snapshot()
        self.doc.fullcopy_page(pno, pno + 1)

    def reorder_pages(self, new_order: list[int]):
        self._snapshot()
        self.doc.select(new_order)

    def insert_pdf(self, path: str, at: int | None = None):
        try:
            src = fitz.open(path)
        except Exception as e:
            raise PdfError(f"Could not open file:\n{e}") from e
        try:
            if not src.is_pdf or src.needs_pass:
                raise PdfError(f"Cannot insert {os.path.basename(path)}: "
                               "not a readable PDF.")
            if self.doc.page_count + src.page_count > MAX_PAGES:
                raise PdfError(
                    f"Inserting {src.page_count} pages would exceed the "
                    f"{MAX_PAGES}-page limit.")
            self._snapshot()
            if at is None:
                self.doc.insert_pdf(src)
            else:
                self.doc.insert_pdf(src, start_at=at)
        finally:
            src.close()

    # ------------------------------------------------------------- annotations

    def add_text_markup(self, pno: int, rects: list[fitz.Rect], kind: str,
                        color: tuple):
        self._snapshot()
        page = self.doc[pno]
        if kind == HIGHLIGHT:
            annot = page.add_highlight_annot(quads=rects)
        elif kind == UNDERLINE:
            annot = page.add_underline_annot(quads=rects)
        else:
            annot = page.add_strikeout_annot(quads=rects)
        annot.set_colors(stroke=color)
        annot.update()

    def add_highlight_box(self, pno: int, rect: fitz.Rect, color: tuple,
                          opacity: float = 0.3):
        """Highlighter: translucent filled box — works without a text layer."""
        self._snapshot()
        annot = self.doc[pno].add_rect_annot(rect)
        annot.set_border(width=0)
        annot.set_colors(stroke=color, fill=color)
        annot.set_opacity(opacity)
        annot.update()

    def add_crossout_box(self, pno: int, rect: fitz.Rect, color: tuple,
                         width: float):
        """Cross-out: box with an X through it, as one ink annotation.

        Visual substitute for strikeout on pages without a text layer.
        """
        self._snapshot()
        r = rect
        strokes = [
            [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1),
             (r.x0, r.y0)],                     # outline
            [(r.x0, r.y0), (r.x1, r.y1)],       # diagonal \
            [(r.x1, r.y0), (r.x0, r.y1)],       # diagonal /
        ]
        annot = self.doc[pno].add_ink_annot(strokes)
        annot.set_border(width=width)
        annot.set_colors(stroke=color)
        annot.update()

    def add_ink(self, pno: int, points: list[fitz.Point], color: tuple,
                width: float):
        self._snapshot()
        stroke = [(p.x, p.y) for p in points]
        annot = self.doc[pno].add_ink_annot([stroke])
        annot.set_border(width=width)
        annot.set_colors(stroke=color)
        annot.update()

    def add_shape(self, pno: int, kind: str, rect: fitz.Rect, color: tuple,
                  width: float):
        self._snapshot()
        page = self.doc[pno]
        annot = (page.add_rect_annot(rect) if kind == "rect"
                 else page.add_circle_annot(rect))
        annot.set_border(width=width)
        annot.set_colors(stroke=color)
        annot.update()

    def add_line(self, pno: int, p1: fitz.Point, p2: fitz.Point, color: tuple,
                 width: float, arrow: bool):
        self._snapshot()
        annot = self.doc[pno].add_line_annot(p1, p2)
        annot.set_border(width=width)
        annot.set_colors(stroke=color)
        if arrow:
            annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE,
                                fitz.PDF_ANNOT_LE_OPEN_ARROW)
        annot.update()

    def page_scale(self, pno: int) -> float:
        """Size multiplier vs a standard letter page.

        Scanned pages carry their DPI in the page size (200 DPI letter =
        1700x2200 units vs 612x792), so fixed point sizes render tiny.
        """
        r = self.doc[pno].rect
        return max(1.0, min(r.width, r.height) / 612.0)

    def add_textbox(self, pno: int, rect: fitz.Rect, text: str,
                    text_color: tuple, fill_color: tuple = (1, 1, 1),
                    fontsize: float = 11, fontname: str = "helv"):
        self._snapshot()
        page = self.doc[pno]
        # rotate= keeps the text upright on rotated pages
        annot = page.add_freetext_annot(
            rect, text, fontsize=fontsize, fontname=fontname,
            text_color=text_color, fill_color=fill_color,
            rotate=page.rotation)
        annot.update()

    def add_callout(self, pno: int, target: fitz.Point, rect: fitz.Rect,
                    text: str, text_color: tuple, fill_color: tuple,
                    fontsize: float = 11, border_width: float = 1.5,
                    fontname: str = "helv"):
        """Speech-bubble FreeText with a callout arrow pointing at target."""
        self._snapshot()
        # tail attaches to the nearest point on the bubble edge
        edge = fitz.Point(max(rect.x0, min(target.x, rect.x1)),
                          max(rect.y0, min(target.y, rect.y1)))
        page = self.doc[pno]
        annot = page.add_freetext_annot(
            rect, text, fontsize=fontsize, fontname=fontname,
            text_color=text_color, fill_color=fill_color,
            callout=(target, edge),
            line_end=fitz.PDF_ANNOT_LE_OPEN_ARROW, rotate=page.rotation)
        annot.set_border(width=border_width)
        annot.update()

    def add_note(self, pno: int, point: fitz.Point, text: str):
        self._snapshot()
        annot = self.doc[pno].add_text_annot(point, text, icon="Note")
        annot.update()

    def note_rects(self, pno: int) -> list[fitz.Rect]:
        """Text (sticky note) annot rects — mupdf renders their icon at a
        fixed 16x16 units, invisible on hi-DPI scans, so the view draws
        its own marker overlay at these positions."""
        page = self.doc[pno]
        return [fitz.Rect(a.rect)
                for a in page.annots(types=[fitz.PDF_ANNOT_TEXT])]

    def redact_area(self, pno: int, rect: fitz.Rect):
        """Immediately black out the area and strip underlying content."""
        self._snapshot()
        page = self.doc[pno]
        page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    def has_redactions(self) -> bool:
        for pno in range(self.doc.page_count):
            for annot in self.doc[pno].annots(
                    types=[fitz.PDF_ANNOT_REDACT]):
                return True
        return False

    def apply_redactions(self) -> int:
        self._snapshot()
        n = 0
        for pno in range(self.doc.page_count):
            page = self.doc[pno]
            n += sum(1 for _ in page.annots(types=[fitz.PDF_ANNOT_REDACT]))
            page.apply_redactions()
        return n

    def annot_at(self, pno: int, point: fitz.Point,
                 tol: float = 3.0) -> tuple | None:
        """Topmost annotation whose rect contains point:
        (xref, rect, type_str, content)."""
        page = self.doc[pno]
        hit = None
        for annot in page.annots():
            r = fitz.Rect(annot.rect)
            r.x0 -= tol; r.y0 -= tol; r.x1 += tol; r.y1 += tol
            if r.contains(point):
                hit = (annot.xref, fitz.Rect(annot.rect), annot.type[1],
                       annot.info.get("content", ""))
        return hit

    def update_note(self, pno: int, xref: int, text: str):
        page = self.doc[pno]
        for annot in page.annots():
            if annot.xref == xref:
                self._snapshot()
                annot.set_info(content=text)
                annot.update()
                return

    def delete_annot_at(self, pno: int, point: fitz.Point,
                        tol: float = 3.0) -> bool:
        """Eraser: delete the topmost annotation whose rect contains point."""
        hit = self.annot_at(pno, point, tol)
        if hit is None:
            return False
        self.delete_annot_by_xref(pno, hit[0])
        return True

    def delete_annot_by_xref(self, pno: int, xref: int):
        page = self.doc[pno]
        for annot in page.annots():
            if annot.xref == xref:
                self._snapshot()
                page.delete_annot(annot)
                return

    # --------------------------------------------------------- move / edit

    @staticmethod
    def _translate_coord_string(val: str, dx: float, dy: float) -> str:
        """Translate every (x, y) pair in a PDF array string like
        "[1 2 3 4]" or nested "[[1 2][3 4]]". Coordinates alternate x, y."""
        out = []
        idx = 0
        for tok in val.replace("[", " [ ").replace("]", " ] ").split():
            if tok in ("[", "]"):
                out.append(tok)
                continue
            try:
                num = float(tok)
            except ValueError:
                out.append(tok)
                continue
            num += dx if idx % 2 == 0 else dy
            idx += 1
            out.append(f"{num:g}")
        return " ".join(out)

    def move_annot(self, pno: int, xref: int, dx: float, dy: float):
        """Move a whole annotation by (dx, dy) given in fitz page space.

        Works for every annotation type: the rendered appearance stream is
        mapped onto /Rect, so translating /Rect (plus the geometry arrays,
        for semantic consistency) moves everything, tails included.
        """
        self._snapshot()
        # PDF object coordinates are y-up; fitz page space is y-down
        ndy = -dy
        for key in ("Rect", "L", "QuadPoints", "CL", "Vertices", "InkList"):
            vtype, val = self.doc.xref_get_key(xref, key)
            if vtype != "null" and val:
                self.doc.xref_set_key(
                    xref, key, self._translate_coord_string(val, dx, ndy))

    def freetext_info(self, pno: int, xref: int) -> dict | None:
        """Content + geometry of a FreeText annot, for re-editing."""
        page = self.doc[pno]
        for annot in page.annots():
            if annot.xref == xref and annot.type[1] == "FreeText":
                r = fitz.Rect(annot.rect)
                info = {"text": annot.info.get("content", ""),
                        "rect": r, "bubble": fitz.Rect(r), "target": None}
                # /RD insets the text bubble inside /Rect (callout tails
                # expand /Rect). RD order [left, pdf-top, right, pdf-bottom]
                # maps to fitz as: x0+RD0, y0+RD3, x1-RD2, y1-RD1 (verified).
                vtype, val = self.doc.xref_get_key(xref, "RD")
                if vtype != "null" and val:
                    rd = [float(t) for t in val.strip("[] ").split() if t]
                    if len(rd) == 4:
                        info["bubble"] = fitz.Rect(r.x0 + rd[0], r.y0 + rd[3],
                                                   r.x1 - rd[2], r.y1 - rd[1])
                vtype, val = self.doc.xref_get_key(xref, "CL")
                if vtype != "null" and val:
                    nums = [float(t) for t in
                            val.strip("[] ").split() if t]
                    if len(nums) >= 2:
                        # CL is y-up PDF space -> convert to fitz y-down
                        h = page.mediabox.height
                        info["target"] = fitz.Point(nums[0], h - nums[1])
                return info
        return None

    def replace_freetext(self, pno: int, xref: int, rect: fitz.Rect,
                         text: str, text_color: tuple, fill_color: tuple,
                         fontsize: float, fontname: str,
                         target: fitz.Point | None,
                         border_width: float = 1.5):
        """Re-create a FreeText annot (textbox or callout) with new content."""
        page = self.doc[pno]
        for annot in page.annots():
            if annot.xref == xref:
                self._snapshot()
                page.delete_annot(annot)
                if target is not None:
                    edge = fitz.Point(max(rect.x0, min(target.x, rect.x1)),
                                      max(rect.y0, min(target.y, rect.y1)))
                    new = page.add_freetext_annot(
                        rect, text, fontsize=fontsize, fontname=fontname,
                        text_color=text_color, fill_color=fill_color,
                        callout=(target, edge),
                        line_end=fitz.PDF_ANNOT_LE_OPEN_ARROW,
                        rotate=page.rotation)
                    new.set_border(width=border_width)
                else:
                    new = page.add_freetext_annot(
                        rect, text, fontsize=fontsize, fontname=fontname,
                        text_color=text_color, fill_color=fill_color,
                        rotate=page.rotation)
                new.update()
                return
