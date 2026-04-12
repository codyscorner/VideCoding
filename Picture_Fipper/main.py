"""
main.py — Entry point for the AutoFlip desktop app.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
