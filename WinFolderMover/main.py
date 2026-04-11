# main.py — application entry point
#
# Usage:
#   pip install PyQt6
#   python main.py

import sys

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    # Fusion gives a clean, modern cross-platform look and plays nicely
    # with the custom stylesheet applied inside MainWindow.
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
