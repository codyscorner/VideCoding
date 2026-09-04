import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox,
    QLineEdit, QScrollArea, QFrame, QFileDialog, QMessageBox, QSizePolicy,
)
from PyQt6.QtGui import QAction, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtCore import Qt

from ui.styles import APP_STYLESHEET, COLORS
from ui.node_section import NodeSection, category_color
from settings import Settings
from workflow_model import WorkflowDoc, parse_workflow


class MainWindow(QMainWindow):
    def __init__(self, version: str, settings: Settings):
        super().__init__()
        self.version = version
        self._settings = settings
        self._path: Path | None = None
        self._doc: WorkflowDoc | None = None
        self._sections: list[NodeSection] = []
        self._category_labels: dict[str, QLabel] = {}
        self._modified = False

        self.setWindowTitle(f"ComfyUI Workflow Editor  v{version}")
        self.resize(860, 920)
        self.setStyleSheet(APP_STYLESHEET)
        self.setAcceptDrops(True)
        self._center_on_screen()

        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

    def _center_on_screen(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def bring_to_front(self):
        """One-time raise on startup so the window isn't buried — not always-on-top."""
        self.raise_()
        self.activateWindow()

    # ── menu ──────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        for label, shortcut, slot in [
            ("&Open…",       "Ctrl+O",       self.open_file),
            (None,           None,            None),
            ("&Save",        "Ctrl+S",       self.save_file),
            ("Save &As…",    "Ctrl+Shift+S", self.save_as),
            (None,           None,            None),
            ("&Quit",        "Ctrl+Q",       self.close),
        ]:
            if label is None:
                file_menu.addSeparator()
            else:
                act = QAction(label, self)
                act.setShortcut(shortcut)
                act.triggered.connect(slot)
                file_menu.addAction(act)

        view_menu = mb.addMenu("&View")
        for label, shortcut, slot in [
            ("&Expand all nodes",   "Ctrl+Shift+E", lambda: self._set_all_expanded(True)),
            ("&Collapse all nodes", "Ctrl+Shift+C", lambda: self._set_all_expanded(False)),
            ("&Find node…",         "Ctrl+F",       self._focus_filter),
        ]:
            act = QAction(label, self)
            act.setShortcut(shortcut)
            act.triggered.connect(slot)
            view_menu.addAction(act)

    # ── toolbar ───────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        for text, slot in [("Open", self.open_file), ("Save", self.save_file)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            tb.addWidget(btn)

        tb.addSeparator()

        self._file_lbl = QLabel("  No file open")
        self._file_lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 9pt;")
        tb.addWidget(self._file_lbl)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet("background: transparent;")   # else it paints as a dark box
        tb.addWidget(spacer)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Find node…  (title, type or #id)")
        self._filter.setClearButtonEnabled(True)
        self._filter.setFixedWidth(230)
        self._filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['fg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 4px 6px;
                font-size: 9pt;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
        """)
        self._filter.textChanged.connect(self._apply_filter)
        tb.addWidget(self._filter)

        self._show_all = QCheckBox("Show all nodes")
        self._show_all.setToolTip("Also show nodes that have no editable settings (every input is a connection)")
        self._show_all.setChecked(bool(self._settings.get("show_all_nodes", False)))
        self._show_all.setStyleSheet(
            f"color: {COLORS['fg_secondary']}; font-size: 9pt; margin-left: 8px; margin-right: 10px;"
        )
        self._show_all.toggled.connect(self._on_show_all_toggled)
        tb.addWidget(self._show_all)

    # ── body (scroll area + empty state) ─────────────────────────────────

    def _build_body(self):
        self._central = QWidget()
        self._central_layout = QVBoxLayout(self._central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)
        self.setCentralWidget(self._central)

        # Empty-state placeholder
        self._empty = QWidget()
        el = QVBoxLayout(self._empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl = QLabel("Open a ComfyUI workflow JSON to begin editing")
        empty_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 12pt;")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_lbl = QLabel("or drag a .json file anywhere onto this window")
        drop_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 9pt;")
        drop_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        open_btn = QPushButton("Open Workflow…")
        open_btn.setFixedWidth(200)
        open_btn.clicked.connect(self.open_file)
        el.addWidget(empty_lbl)
        el.addSpacing(4)
        el.addWidget(drop_lbl)
        el.addSpacing(16)
        el.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._central_layout.addWidget(self._empty)

        # Scroll area (hidden until a file is loaded)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setAcceptDrops(False)
        self._scroll.viewport().setAcceptDrops(False)
        self._scroll.hide()
        self._central_layout.addWidget(self._scroll)

    def _build_statusbar(self):
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; padding: 2px 6px;")
        self.statusBar().addWidget(self._status_lbl)

    # ── form builder ──────────────────────────────────────────────────────

    def _build_form(self):
        """Build one NodeSection per node, grouped under category headings."""
        self._sections.clear()
        self._category_labels.clear()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 12, 20, 24)
        layout.setSpacing(8)

        current_cat = None
        for node in self._doc.nodes:
            if node.category != current_cat:
                current_cat = node.category
                cat_lbl = QLabel(current_cat.upper())
                cat_lbl.setStyleSheet(
                    f"color: {category_color(current_cat)}; font-size: 8pt; font-weight: bold;"
                    f"letter-spacing: 1px; margin-top: 10px; margin-bottom: 2px;"
                )
                layout.addWidget(cat_lbl)
                self._category_labels[current_cat] = cat_lbl

            section = NodeSection(node, self._mark_modified)
            self._sections.append(section)
            layout.addWidget(section)

        layout.addStretch()
        self._scroll.setWidget(container)
        self._disable_child_drops(container)
        self._apply_filter()

    @staticmethod
    def _disable_child_drops(root: QWidget):
        """Stop form widgets from swallowing file drops so the window handles them.

        QTextEdit/QLineEdit/QSpinBox accept text drags by default, which would paste
        the dropped path into a field instead of opening the workflow.
        """
        for child in root.findChildren(QWidget):
            child.setAcceptDrops(False)
            viewport = getattr(child, "viewport", None)
            if callable(viewport):
                vp = viewport()
                if vp is not None:
                    vp.setAcceptDrops(False)
        root.setAcceptDrops(False)

    # ── view helpers ──────────────────────────────────────────────────────

    def _apply_filter(self, *_):
        needle = self._filter.text().strip()
        show_all = self._show_all.isChecked()
        visible_by_cat: dict[str, int] = {}
        shown = 0
        for section in self._sections:
            visible = section.matches(needle) and (show_all or section.has_settings or bool(needle))
            section.setVisible(visible)
            if visible:
                shown += 1
                cat = section.node.category
                visible_by_cat[cat] = visible_by_cat.get(cat, 0) + 1
        for cat, lbl in self._category_labels.items():
            lbl.setVisible(visible_by_cat.get(cat, 0) > 0)
        if self._doc and (needle or not show_all):
            self._status_lbl.setText(f"{self._base_status()}  —  showing {shown} of {len(self._sections)} nodes")
        elif self._doc:
            self._status_lbl.setText(self._base_status())

    def _on_show_all_toggled(self, on: bool):
        self._settings.set("show_all_nodes", bool(on))
        self._apply_filter()

    def _set_all_expanded(self, expanded: bool):
        for section in self._sections:
            section.set_expanded(expanded)

    def _focus_filter(self):
        self._filter.setFocus()
        self._filter.selectAll()

    def _base_status(self) -> str:
        if not self._doc or not self._path:
            return "Ready"
        fmt = "API format" if self._doc.fmt == "api" else "UI graph format"
        return (f"{self._path.name}  —  {fmt}  —  {len(self._doc.nodes)} nodes"
                f"  —  {self._doc.editable_field_count} editable fields")

    # ── file operations ───────────────────────────────────────────────────

    def open_file(self):
        if not self._confirm_discard():
            return
        start_dir = self._settings.get("last_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ComfyUI Workflow", start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        self.load_path(Path(path))

    def load_path(self, path: Path) -> bool:
        """Load a workflow JSON from disk and rebuild the form. Returns True on success."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", f"Could not load:\n{exc}")
            return False

        try:
            doc = parse_workflow(data)
        except ValueError as exc:
            QMessageBox.critical(self, "Open failed", f"{path.name} is not a ComfyUI workflow — {exc}.")
            return False

        self._path = path
        self._settings.set("last_dir", str(path.parent))
        self._doc = doc
        self._modified = False

        self._empty.hide()
        self._scroll.show()
        self._build_form()
        self._update_title()

        self._status_lbl.setText(self._base_status())
        self._file_lbl.setText(f"  {path.name}")
        self._apply_filter()
        return True

    def _confirm_discard(self) -> bool:
        """Ask about unsaved changes before replacing the workflow that is open."""
        if not self._modified:
            return True
        reply = QMessageBox.question(
            self, "Unsaved changes",
            "You have unsaved changes. Save before opening another workflow?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            self.save_file()
            return not self._modified
        return reply == QMessageBox.StandardButton.Discard

    def save_file(self):
        if self._doc is None:
            return
        if self._path is None:
            self.save_as()
            return
        self._commit_and_save(self._path)

    def save_as(self):
        if self._doc is None:
            return
        start_dir = str(self._path.parent) if self._path else self._settings.get("last_dir", "")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Workflow As", start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        self._commit_and_save(Path(path))

    def commit_edits(self):
        """Write every editor widget's value back into the workflow data."""
        for section in self._sections:
            for binding in section.bindings:
                binding.commit()

    def _commit_and_save(self, path: Path):
        self.commit_edits()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._doc.data, f, indent=2, ensure_ascii=False)
            self._path = path
            self._settings.set("last_dir", str(path.parent))
            self._modified = False
            self._update_title()
            self._status_lbl.setText(f"Saved  —  {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save:\n{exc}")

    # ── drag and drop ─────────────────────────────────────────────────────

    @staticmethod
    def _dropped_json_paths(mime) -> list[Path]:
        """Local .json files carried by a drag, in the order they were dropped."""
        if not mime.hasUrls():
            return []
        paths = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".json" and path.is_file():
                paths.append(path)
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self._dropped_json_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if self._dropped_json_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = self._dropped_json_paths(event.mimeData())
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()

        if not self._confirm_discard():
            return
        if self.load_path(paths[0]) and len(paths) > 1:
            self._status_lbl.setText(
                f"{self._status_lbl.text()}  (opened first of {len(paths)} dropped files)"
            )

    # ── helpers ───────────────────────────────────────────────────────────

    def _mark_modified(self, *_):
        if not self._modified:
            self._modified = True
            self._update_title()

    def _update_title(self):
        base = f"ComfyUI Workflow Editor  v{self.version}"
        if self._path:
            marker = " *" if self._modified else ""
            self.setWindowTitle(f"{base}  —  {self._path.name}{marker}")
        else:
            self.setWindowTitle(base)

    def closeEvent(self, event):
        if not self._modified:
            event.accept()
            return
        reply = QMessageBox.question(
            self, "Unsaved changes",
            "You have unsaved changes. Save before closing?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            self.save_file()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()
