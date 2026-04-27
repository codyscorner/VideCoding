import sys
import json
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QFileDialog
from PyQt6.QtGui import QPainter, QImage, QAction, QTransform, QKeySequence
from PyQt6.QtCore import Qt, QRectF

from bb_constants import BACKGROUND
from bb_scene import BlackboardScene
from bb_view import BlackboardView
from bb_sidebar import SidebarPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataFlow Blackboard Architect")
        self.resize(1440, 880)

        self.scene   = BlackboardScene(-5000, -5000, 10000, 10000)
        self.view    = BlackboardView(self.scene)
        self.sidebar = SidebarPanel(self.view)

        self._build_menubar()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.sidebar)
        body.addWidget(self.view)

        container = QWidget()
        container.setLayout(body)
        self.setCentralWidget(container)

    def _build_menubar(self):
        mb = self.menuBar()

        def _act(text, slot, shortcut=None) -> QAction:
            a = QAction(text, self)
            a.triggered.connect(slot)
            if shortcut is not None:
                a.setShortcut(shortcut)
            return a

        file_menu = mb.addMenu("File")
        file_menu.addAction(_act("New",            self._new_canvas,  QKeySequence.StandardKey.New))
        file_menu.addAction(_act("Open…",          self._load_canvas, QKeySequence.StandardKey.Open))
        file_menu.addAction(_act("Save…",          self._save_canvas, QKeySequence.StandardKey.Save))
        file_menu.addSeparator()
        file_menu.addAction(_act("Export 4K PNG…", self._export_4k))
        file_menu.addSeparator()
        file_menu.addAction(_act("Exit",           self.close, QKeySequence.StandardKey.Quit))

        edit_menu = mb.addMenu("Edit")
        undo_act  = self.scene.undo_stack.createUndoAction(self, "Undo")
        redo_act  = self.scene.undo_stack.createRedoAction(self, "Redo")
        undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(undo_act)
        edit_menu.addAction(redo_act)
        edit_menu.addSeparator()
        edit_menu.addAction(_act("Delete Selected", self.scene.delete_selected,
                                 QKeySequence(Qt.Key.Key_Delete)))

    def _new_canvas(self):
        self.scene.clear()
        self.scene.undo_stack.clear()

    def _save_canvas(self):
        t = self.view.transform()
        data = self.scene.to_dict({"m11": t.m11(), "m22": t.m22(),
                                    "dx": t.dx(),  "dy": t.dy()})
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Canvas", "", "DataFlow Files (*.dflow)")
        if path:
            if not path.endswith(".dflow"):
                path += ".dflow"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def _load_canvas(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Canvas", "", "DataFlow Files (*.dflow)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vd = self.scene.from_dict(data)
        if vd:
            self.view.setTransform(QTransform(
                vd.get("m11", 1), 0, 0,
                vd.get("m22", 1), vd.get("dx", 0), vd.get("dy", 0)))

    def _export_4k(self):
        sr = self.scene.itemsBoundingRect()
        if sr.isEmpty():
            return
        sr = sr.adjusted(-40, -40, 40, 40)
        image = QImage(3840, 2160, QImage.Format.Format_ARGB32)
        image.fill(BACKGROUND)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(painter, QRectF(image.rect()), sr)
        painter.end()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export 4K PNG", "", "PNG Files (*.png)")
        if path:
            image.save(path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
